from json import loads
from uuid import uuid4

from rpy2 import robjects
from rpy2.robjects import IntVector

from py2r.rUtils import execute_r, execute_r2
from py2r.pylogger import logger


def openblankdataset(datasetName):
    # Fresh data under this name -- drop/invalidate any Replace All undo tokens.
    _replace_clear(datasetName)
    open_cmd = f"BSkyOpenNewDataset(datasetName='{datasetName}', noOfRows=80,noOfCols=15)"
    yield {"message": open_cmd, "name": datasetName, "type": "log"}
    robjects.r(open_cmd)
    for message in getrowcountcolprops(datasetName):
        yield message["message"]


def open(file_path, filetype, wsName, replace_ds, csvHeader, char_to_factor, basket_data, csv_sep, delim, groupingchar,
         datasetName, encoding, cgid):
    # Fresh data under this name -- drop/invalidate any Replace All undo tokens.
    _replace_clear(datasetName)
    if filetype == 'SAV':
        filetype = 'SPSS'
    open_cmd = f"BSkyloadDataset(fullpathfilename='{file_path}', " \
               f"filetype='{filetype}', " \
               f"worksheetName={wsName}, " \
               f"replace_ds={replace_ds}, " \
               f"load.missing=FALSE, " \
               f"csvHeader={csvHeader}, " \
               f"character.to.factor={char_to_factor}, " \
               f"isBasketData={basket_data}, " \
               f"trimSPSStrailing=FALSE, " \
               f"sepChar='{csv_sep}', " \
               f"deciChar='{delim}', " \
               f"groupingChar='{groupingchar}', " \
               f"encoding={encoding}, " \
               f"datasetName='{datasetName}')"
    yield {"message": open_cmd, "name": datasetName, "type": "syntax", "error": "", "parent_id": cgid}
    content = robjects.r(open_cmd)
    if content is None or (isinstance(content, list) and content[1] == 'NILSXP'):
        content = ""
    else:
        content = content[0]
    if content == 0:
        for message in getrowcountcolprops(datasetName, True, file_path):
            yield message["message"]


def close(datasetName):
    # Free/invalidate this dataset's Replace All undo tokens on close.
    _replace_clear(datasetName)


def refresh(datasetName: str, reloadCols: bool = True, fromrowidx: int = 1, torowidx: int = 20, digits: int = 'NA',
            signalReloadColsUI: bool = False):
    # signalReloadColsUI: stamp reloadCols=True onto the outgoing message so the grid's
    # newDataFrame handler rebuilds the column definitions (formatters/editors and the
    # factor dropdown's dataSource). Needed when a column's metadata changed WITHOUT a
    # type change -- e.g. a new factor level -- which colTypeMismatch alone does not catch.
    res = {}
    for message in getrowcountcolprops(datasetName, reloadCols=reloadCols):
        res = message
    if (res['message']['rowcount'] < torowidx):
        torowidx = res['message']['rowcount']
    # https://www.rdocumentation.org/packages/jsonlite/versions/1.9.1/topics/toJSON%2C%20fromJSON
    df, _ = execute_r(f'jsonlite::toJSON({datasetName}[{fromrowidx}:{torowidx},], na=NULL, digits={digits})')
    df = loads(df[0])
    try:
        df_list = [list(df[0].keys())]
        for row in df:
            df_list.append(list(row.values()))
            # cols no needed in following and reloadCols should be False
    except AttributeError:
        df_list = []
        for row in df:
            df_list.append([row])
    res["message"]["df"] = df_list
    res["message"]["fromidx"] = fromrowidx
    res["message"]["toidx"] = torowidx
    res["message"]["digits"] = digits
    # Frontend reads resp.message.reloadCols to decide whether to rebuild columns.
    if signalReloadColsUI:
        res["message"]["reloadCols"] = True

    yield {
        "message": res,
        "refresh": True,
        "name": datasetName,
        "fromidx": fromrowidx,
        "toidx": torowidx,
        'digits': digits
    }


def load(datasetName):
    yield {"message": f"Loading Dataset {datasetName}", "name": datasetName, "type": "log"}
    for message in getrowcountcolprops(datasetName):
        yield message["message"]

def getcell(datasetName: str, row: int, col: int, digits: str = 'NA'):
    # row and col are 1-based (R indexing). col is the data column index
    # (1 = first data column, matching SlickGrid's editCommand.c).
    r_cmd = f'jsonlite::toJSON(.GlobalEnv${datasetName}[[{col}]][{row}], na=NULL, digits={digits})'
    value, _ = execute_r(r_cmd)
    cell_value = loads(value[0])
    if isinstance(cell_value, list) and len(cell_value) > 0:
        cell_value = cell_value[0]
    yield {
        "type": "cellupdate",
        "datasetName": datasetName,
        "row": row,
        "col": col,
        "value": cell_value
    }


def search(datasetName: str, term: str, maxMatches: int = 10000):
    # Find & navigate (Ctrl+F): locate every cell whose displayed text *contains*
    # `term`, case-insensitively. Returns 1-based (row, col) coordinates, row-major
    # sorted. 
    if term is None or term == "":
        yield {"type": "searchResult", "name": datasetName, "term": term,
               "matches": [], "total": 0, "truncated": False}
        return

    # Escape only what an R double-quoted string literal needs.
    safe_term = term.replace("\\", "\\\\").replace('"', '\\"')

    # Delegates to the BSkySearchDataset() R function (see BSkySearchDataset.R).
    r_expr = (
        f'BSkySearchDataset('
        f'"{datasetName}", "{safe_term}", {int(maxMatches)})'
    )

    result, _ = execute_r(r_expr)
    obj = loads(result[0]) if result and result[0] else {}
    total = obj.get("total", [0])
    total = total[0] if isinstance(total, list) else total
    pairs = obj.get("matches", []) or []
    matches = [{"row": int(p[0]), "col": int(p[1])} for p in pairs]

    yield {
        "type": "searchResult",
        "name": datasetName,
        "term": term,
        "matches": matches,
        "total": total,
        "truncated": total > len(matches),
    }


# ---------------------------------------------------------------------------
# Find & Replace All (undoable, virtual-grid friendly)
#
# Replace All applies one replacement to every scoped/highlighted match in a
# single R transaction. R keeps the *pre-image* (the old values) and the
# *post-image* under a `token`; the browser stores only that token, so undo /
# redo cost O(1) browser memory no matter how many cells were replaced -- the
# whole dataset never has to be loaded into SlickGrid.
#
# Lifecycle (all enforced in R):
#   * Bound     -- at most `maxStack` (20) tokens are retained per dataset;
#                  the oldest is evicted, mirroring the JS undo buffer size.
#   * Invalidate on reopen -- each dataset carries a monotonically increasing
#                  loadId. `.bskyReplaceClear` bumps it (called on open/close),
#                  so any token minted against the old data is rejected by
#                  `.bskyReplaceRestore` even if its entry still lingers -- row
#                  identity may have changed, so a stale undo must never apply.
#   * Free on close/reopen -- `.bskyReplaceClear` also drops that dataset's
#                  entries so column snapshots are not leaked for the session.
#
# The helper functions themselves (.bskyReplaceInit / .bskyReplaceLoadId /
# .bskyReplaceClear / .bskyReplaceApplyAll / .bskyReplaceRestore) live in the
# BlueSky R package, so they are already defined in globalenv when the package
# is loaded -- we just call them here, the same way we call BSkyLoadRefresh /
# UAgetColProperties / BSkyloadDataset. The R side returns plain R lists; JSON
# serialization stays on this (Python) side via jsonlite::toJSON(...) so the
# package functions remain reusable from R without forcing a JSON round-trip.
# ---------------------------------------------------------------------------


def _r_str_escape(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def _scalar(v, default=None):
    # jsonlite may return length-1 vectors as bare scalars (auto_unbox) or lists.
    if isinstance(v, list):
        return v[0] if v else default
    return v if v is not None else default


def _replace_clear(datasetName):
    """Lifecycle hook: invalidate + drop a dataset's replace tokens.

    Called when the dataset is opened (fresh data under the same name) or closed.
    Bumps the R-side loadId so any still-referenced token is rejected on undo, and
    frees the retained column snapshots.
    """
    try:
        robjects.r(f'.bskyReplaceClear("{_r_str_escape(datasetName)}")')
    except Exception:
        pass


def replace_all(datasetName, replacement, rows, cols, fromrowidx=1, torowidx=20,
                requestId=None, digits='NA'):
    # Apply `replacement` at every (rows[k], cols[k]) match in one R transaction,
    # emit the undo `token`, then repaint just the current viewport so off-screen
    # rows never touch the grid.
    token = 'rpl_' + uuid4().hex
    robjects.globalenv['.bsky_rpl_rows'] = IntVector([int(x) for x in rows])
    robjects.globalenv['.bsky_rpl_cols'] = IntVector([int(x) for x in cols])
    expr = (
        f'jsonlite::toJSON(.bskyReplaceApplyAll('
        f'"{_r_str_escape(datasetName)}", .bsky_rpl_rows, .bsky_rpl_cols, '
        f'"{_r_str_escape(replacement)}", "{token}"), auto_unbox = TRUE)'
    )
    result, _ = execute_r(expr)
    robjects.r('if (exists(".bsky_rpl_rows")) rm(.bsky_rpl_rows); '
               'if (exists(".bsky_rpl_cols")) rm(.bsky_rpl_cols)')
    # TEMP DEBUG: dump the R dataframe after this replace so successive find/replace
    # calls can be compared. head(30) keeps it within the rotating log's size. Remove when done.
    
    obj = loads(result[0]) if result and result[0] else {}
    replaced = int(_scalar(obj.get('replaced'), 0) or 0)
    cols_changed = bool(_scalar(obj.get('colsChanged'), False))

    yield {
        "type": "replaceResult",
        "op": "replaceall",
        "name": datasetName,
        "requestId": requestId,
        "token": _scalar(obj.get('token'), token),
        "replaced": replaced,
        "colsChanged": cols_changed,
        "ok": True,
    }
    # A factor/type change (colsChanged) means BlueSky's column metadata is now stale.
    # UAgetColProperties reads that metadata for the grid's factor dropdown (dataSource),
    # and a bare df reassignment does NOT update it -- so a newly added factor level would
    # never appear in the dropdown (shows "--"). BSkyLoadRefresh regenerates the metadata;
    # load.dataframe=FALSE keeps it metadata-only (no BlueSky UI reload) since we drive the
    # viewport repaint ourselves via refresh(). Mirrors the Add-New-Levels dialog, which
    # also calls BSkyLoadRefresh after fct_expand.
    if cols_changed:
        try:
            robjects.r(f'BSkyLoadRefresh("{_r_str_escape(datasetName)}", load.dataframe = FALSE)')
        except Exception:
            pass

    # reloadCols=True is required, not just an optimization: with reloadCols=False the
    # refresh returns cols=[], which the newDataFrame handler reads as a single-row
    # post-edit correction (isSingleRow) and skips the multi-row viewport repaint. It
    # also lets that handler auto-detect a column type change (colTypeMismatch) and
    # rebuild the column formatter/editor when a replace coerces a column's type.
    # signalReloadColsUI forces that rebuild even without a type change (e.g. a new factor
    # level), so the dropdown's dataSource picks up the level UAgetColProperties now returns.
    for msg in refresh(datasetName, reloadCols=True, signalReloadColsUI=cols_changed,
                       fromrowidx=fromrowidx, torowidx=torowidx, digits=digits):
        yield msg


def _replace_op(datasetName, token, op, which, fromrowidx=1, torowidx=20,
                requestId=None, digits='NA'):
    expr = (
        f'jsonlite::toJSON(.bskyReplaceRestore('
        f'"{_r_str_escape(token)}", "{which}"), auto_unbox = TRUE)'
    )
    result, _ = execute_r(expr)
    
    obj = loads(result[0]) if result and result[0] else {}
    ok = bool(_scalar(obj.get('ok'), False))
    cols_changed = bool(_scalar(obj.get('colsChanged'), False))
    ds = _scalar(obj.get('dataset'), datasetName) or datasetName

    yield {
        "type": "replaceResult",
        "op": op,
        "name": ds,
        "requestId": requestId,
        "ok": ok,
        "colsChanged": cols_changed,
    }
    if ok:
        # Undo/redo of a factor replace swaps the whole column snapshot (levels included),
        # so BlueSky's metadata and the grid's dropdown must be regenerated/rebuilt too --
        # same reasoning as replace_all above.
        if cols_changed:
            try:
                robjects.r(f'BSkyLoadRefresh("{_r_str_escape(ds)}", load.dataframe = FALSE)')
            except Exception:
                pass
        # reloadCols must be True (not cols_changed): undo/redo of a Replace All is a
        # multi-cell change, and with reloadCols=False the refresh returns cols=[], which
        # the newDataFrame handler treats as a single-row correction (isSingleRow) and
        # skips the multi-row viewport repaint -- so the grid never updates on undo/redo.
        # Same requirement as replace_all. signalReloadColsUI stays gated on cols_changed
        # since column defs only need rebuilding on an actual type/factor-level change.
        for msg in refresh(ds, reloadCols=True, signalReloadColsUI=cols_changed,
                           fromrowidx=fromrowidx, torowidx=torowidx, digits=digits):
            yield msg


def replace_undo(datasetName, token, fromrowidx=1, torowidx=20, requestId=None, digits='NA'):
    yield from _replace_op(datasetName, token, 'replaceundo', 'pre',
                           fromrowidx, torowidx, requestId, digits)


def replace_redo(datasetName, token, fromrowidx=1, torowidx=20, requestId=None, digits='NA'):
    yield from _replace_op(datasetName, token, 'replaceredo', 'post',
                           fromrowidx, torowidx, requestId, digits)


def getrowcountcolprops(datasetName,reloadCols=True,file_path ="" ):
    rc, _ = execute_r(f'jsonlite::toJSON(nrow(.GlobalEnv${datasetName}))')
    rc = loads(rc[0])
    cc, _ = execute_r(f'jsonlite::toJSON(ncol(.GlobalEnv${datasetName}))')
    cc = loads(cc[0])
    res = {"name": datasetName, "cols": [], "rowcount": rc[0], "colcount": cc[0], "type": "rccolprop",
           "file_path": file_path}  # rccolprop = rowcount-colprop
    if reloadCols:
        for index in range(1, cc[0] + 1):
            col_details_cmd = f"data=UAgetColProperties(dataSetNameOrIndex='.GlobalEnv${datasetName}', colNameOrIndex={index}, " \
                              f"asClass=FALSE, isDSValidated=TRUE);"
            execute_r2(col_details_cmd)
            col, _ = execute_r("jsonlite::toJSON(data, na = NULL)")
            res["cols"].append(loads(col[0]))
    yield {
        "message": res,
        "refresh": True,
        "name": datasetName
    }
