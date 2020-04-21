import os
import bs4
import regex
import shutil
from bs4 import BeautifulSoup


def main():

    off = "\t"

    TXT_DIR = "theatregratuit-txt"
    fnames, n_files = get_fnames(TXT_DIR)

    # save trimmed files to dir
    TRIM_DIR = "trimmed"
    check_create_dir(TRIM_DIR)

    # if trimming already happened, just load the files
    if len(os.listdir(TRIM_DIR)) == 0:
        DATA = get_all_data(fnames, n_files, TXT_DIR, TRIM_DIR)
    else:
        DATA = get_all_data(fnames, n_files, TXT_DIR, TRIM_DIR, load=True)

    fnames_ratio = []
    pattern = r"\b\p{Lu}{4,}\b"
    for i, (f, data) in enumerate(DATA.items()):
        print(f"{i:4}/{n_files} | calculating ratio for: {pattern} | {f}")
        r = matches_to_lines_ratio(data, pattern)
        fnames_ratio = binary_insert(fnames_ratio, (f,r))

    separator_print()
    for x in fnames_ratio:
        print(f"ratio: {x[1]:0.2f} | {x[0]}")

    # # splitting
    # save_split_groups(
    #     "^[\p{Lu}]+[\p{Z}\p{P}]*$",
    #     DATA,
    #     le_dir=TRIM_DIR,
    #     threshold=10,
    #     le_dir_with="with",
    #     le_dir_without="without",
    #     verbose=True,
    # )

    # # formatting
    # FORM_DIR = "formatted"
    # check_create_dir(FORM_DIR, clean=True)

    # for i, (f, data) in enumerate(DATA.items()):
    #     print(f"{i+1:4}/{n_files} | attempting formatting of: {TRIM_DIR}/{f}")
    #     data = format_caps(data)
    #     if "formatted" in data:
    #         save_lines(f, data["formatted"], le_dir=FORM_DIR)

    # separator_print()
    # underprint(f"first pass done: files with characters in caps | saved to {FORM_DIR}/")

    # REST_DIR = "rest"
    # check_create_dir(REST_DIR, clean=True)

    # UNFORMATTED = {}
    # for i, (f, data) in enumerate(DATA.items()):
    #     if "unformatted" in data:
    #         UNFORMATTED[f] = data
    # n_unf = len(UNFORMATTED.keys())

    # for i, (f, data) in enumerate(UNFORMATTED.items()):
    #     print(f"{i+1:4}/{n_unf} | writing: {REST_DIR}/{f}")
    #     save_lines(f, data["unformatted"], le_dir=REST_DIR)

    # separator_print()
    # underprint(f"saved unformatted files to {REST_DIR}/")

    # ds_dir = "theatregratuit-dataset"
    # if not os.path.isdir(ds_dir):
    #     os.mkdir(ds_dir)


# ----------------------------------------
# splitting corpus


def save_split_groups(
    reg,
    data_dict,
    le_dir,
    threshold=1,
    le_dir_with="with",
    le_dir_without="without",
    verbose=True,
):
    check_create_dir(le_dir_with, clean=True)
    check_create_dir(le_dir_without, clean=True)
    with_it, without = split_by_regex(
        data_dict, reg, threshold=threshold, verbose=verbose
    )
    print(f"files with pattern saved to {le_dir_with}")
    print(f"files without pattern saved to {le_dir_without}")
    for i, f in enumerate(with_it):
        shutil.copyfile(os.path.join(le_dir, f), os.path.join(le_dir_with, f))
    for i, f in enumerate(without):
        shutil.copyfile(os.path.join(le_dir, f), os.path.join(le_dir_without, f))


def split_by_regex(data_dict, pattern, threshold=1, verbose=True):
    with_pattern = []
    without_pattern = []
    if verbose:
        underprint(f"splitting data: is there {threshold} occurrences of {pattern}?")
    total = len(data_dict.keys())
    for i, (fname, data) in enumerate(data_dict.items()):
        if verbose:
            print(f"{i+1:4}/{total} | searching in {fname}")
        found = 0
        for l in data["trimmed"]:
            if regex.search(pattern, l):
                found += 1
                if found == threshold:
                    break
        if found == threshold:
            with_pattern.append(fname)
        else:
            without_pattern.append(fname)
    if verbose:
        separator_print()
        print(f"pattern:       {pattern}")
        print(f"files with:    {len(with_pattern)}")
        print(f"files without: {len(without_pattern)}")
    return with_pattern, without_pattern


def matches_to_lines_ratio(data, pattern, verbose=False):
    f = data["fname"]
    lines = data["trimmed"]
    lines_len = data["trimmed_len"]
    n_matches = 0
    for l in lines:
        n_matches += len(regex.findall(pattern, l))
    r = n_matches / lines_len
    if verbose:
        print(f"ratio: {r:.2f} | n_matches: {n_matches:4} for {lines_len:4} lines | {f}")
    return r


# ----------------------------------------
# Formatting


def format_caps(data):

    formatted = ["<|s|>"]

    if data["fname"] in (
        "count-1004248-LARTICLE_330_-_Georges_Courteline.txt",
        "count-1004275-LIMPROMPTU_DE_VERSAILLES_-_Moliere.txt",
        "count-1004244-LIOLA_-_Luigi_Pirandello.txt",
        "count-1004282-MAGDA_EST_LA_ET_NEST_PAS_LA_-_Jean_Sibil.txt",
        "count-1029795-HOTEL_DU_LIBRE-ECHANGE_II_-_Jean_Sibil.txt",
        "count-1045935-Le_Pendu_-_Charles_Cros.txt ",
        "count-1045947-Lhomme_propre_-_Charles_Cros.txt",
        "count-1072551-dodutt.txt",
        "count-1396213-Roberto_Succo.txt",
        "count-1470266-LElecteur.txt",
        "count-1470267-SUZANNE_ET_LES_VENERABLES.txt ",
        "count-1045935-Le_Pendu_-_Charles_Cros.txt ",
        "count-1470267-SUZANNE_ET_LES_VENERABLES.txt",
    ):
        formatted.extend(data["trimmed"])
        # add very end markers, trim lines
        formatted = markers_final_cleanup(formatted)
        data["unformatted"] = formatted
        return data

    # skip first match, so that entire start of text caught in one extract
    # (adding <|s|> at the very top of file after the loop)
    skipped = False

    for j, l in enumerate(data["trimmed"]):

        # remove footnote calls (digit)
        l = regex.sub(R["(footnote)"], "", l)

        # ------------------------------------------------------------------------
        # FAT MAJORITY: CAPS

        # check for full caps line
        caps_line = regex.match(R["LINE"], l)
        if caps_line and not regex.match(R["WORD_INIT"], formatted[-1]):
            formatted, skipped = append_markers(formatted, skipped)
            l = regex.sub(R["trailing_punct"], "", l) + "."
            formatted.append(l)
            continue

        # init capital letters word
        word_init = regex.match(R["WORD_INIT"], l)
        # check that previous line is not already with full caps
        if word_init:

            rest = l[word_init.span()[1] :]

            # is there a dot'n'dash straight away?
            dot_n_dash = regex.match(R["dot_n_dash"], rest)
            cont, formatted, skipped = append_splits(
                formatted, R["dot_n_dash"], l, rest, skipped, word_init.span()[1]
            )
            if cont:
                continue

            # is there a colon straight away?
            cont, formatted, skipped = append_splits(
                formatted, R["colon"], l, rest, skipped, word_init.span()[1]
            )
            if cont:
                continue

            # get all caps words on the line, and check the last one,
            # find the last one (https://stackoverflow.com/a/2988680)
            more_caps_words = regex.finditer(R["WORD"], l)
            last_caps_word = None
            for last_caps_word in more_caps_words:
                pass
            if last_caps_word:

                rest = l[last_caps_word.span()[1] :]

                if rest:

                    # check for colon
                    cont, formatted, skipped = append_splits(
                        formatted,
                        R["colon"],
                        l,
                        rest,
                        skipped,
                        last_caps_word.span()[1],
                    )
                    if cont:
                        continue

                    # check for comma and dash
                    cont, formatted, skipped = append_splits(
                        formatted,
                        R["comma_dash"],
                        l,
                        rest,
                        skipped,
                        last_caps_word.span()[1],
                    )
                    if cont:
                        continue

                    # check for didascalia: find colon later
                    cont, formatted, skipped = append_splits(
                        formatted,
                        R["colon"],
                        l,
                        rest,
                        skipped,
                        last_caps_word.span()[1],
                        search=True,
                    )
                    if cont:
                        continue

                    # check for didascalia: find either dot or dot'n'dash later
                    cont, formatted, skipped = append_splits(
                        formatted,
                        R["dot_opt_dash"],
                        l,
                        rest,
                        skipped,
                        last_caps_word.span()[1],
                        search=True,
                    )
                    if cont:
                        continue

                else:

                    formatted, skipped = append_markers(formatted, skipped)
                    formatted.append(l[: last_caps_word.span()[1]] + ".")
                    continue

            more_caps_words, last_caps_word = None, None  # needs reset

        # otherwise just append the line
        formatted.append(l)

    # add very end markers, trim lines
    formatted = markers_final_cleanup(formatted)

    # save lines
    if not skipped:
        data["unformatted"] = formatted
    else:
        data["formatted"] = formatted

    return data


def append_splits(formatted, reg, l, rest, skipped, end_ind, search=False):
    if search:
        reg_re = regex.search(reg, rest)
    else:
        reg_re = regex.match(reg, rest)
    if reg_re:
        formatted, skipped = append_markers(formatted, skipped)
        if search:  # end of prefix just after didascalia, before boundary punctuation
            end_ind += reg_re.span()[0]
        start = l[:end_ind] + "."
        formatted.append(start)
        formatted = check_append(formatted, rest[reg_re.span()[1] :])
        return True, formatted, skipped
    else:
        return False, formatted, skipped


def append_markers(lines, skipped):
    """will append markers, and turn skipped to true"""
    if skipped and not regex.search(R["WORD_INIT"], lines[-1]):
        lines.append("<|e|>")
        lines.append("<|s|>")
    return lines, True


def check_append(lines, bit):
    if bit:
        lines.append(bit)
    return lines


def markers_final_cleanup(lines):
    lines = remove_trailing_lines(lines)
    lines.append("<|e|>")
    return lines


def remove_trailing_lines(lines):
    if regex.match(R["blank_line"], lines[-1]):
        for i, l in enumerate(reversed(lines)):
            if not regex.match(R["blank_line"], l):
                return lines[:-i]
    else:
        return lines


# ---------------------------------------
# Les Regices


def make_regices():
    return {
        "blank_line": regex.compile("^\s*$"),
        "blank_line_with_rubbish": regex.compile("^[\p{Z}\p{P}]*$"),
        # trim beginning & end of files
        # -----------------------------
        "character": regex.compile(
            "^((les\s*)*pe*rsonna *ge|(les)*acteurs|dramatis personae|avertissement|entreparleur|biographies|apparences|personrage|persongueules|pépersonâge)",
            regex.IGNORECASE,
        ),
        "author": regex.compile("^de$", regex.IGNORECASE),
        "additional_author": regex.compile(
            "^(\(Auteur inconnu\)|"
            + "Voltaire|"
            + "de\s+Georges Courteline|"
            + "Translation en prose de Jean Sibil|"
            + "Anton Pavlovitch Tchekhov|"
            + "EUGENE LABICHE, A. LEFRANC et MARC-MICHEL|"
            + "Alexandre Hardy)$"
        ),
        "la_scene": regex.compile("^La scène"),
        "fin": regex.compile("(fin|rideau|f1n|inachev|manque)", regex.IGNORECASE),
        # search for lines made of full caps + punct/space, as well as some
        # very common words listing characters, and didascalia in ()
        "LINE": regex.compile(
            "^((\p{Lu}+|seule?|puis|puis tout le monde|moins|et)[\p{Z}\p{P}]*)+\p{Z}*"
            + "(\(.*?\))*\p{Z}*$"
        ),
        "(line)": regex.compile("^\(.*\)$"),
        # common annoying starts "M.", "L'"
        "annoying_init": regex.compile("^[\p{P}\p{Z}]*(M\.|\p{Lu}')\p{Z}*"),
        # words (with possible - or '), and space, with punctuation at the end
        "caps_init": regex.compile(
            "^\s*(([\p{Lu}\p{Pc}\p{Pd}1]+\p{Zs}*)+)(\s*[\p{Po}]\s*)"
        ),
        "char_lc_dot_dash": regex.compile(
            "^(\p{Z}*M*[\p{Ll}\p{Z}]+\.)\p{Z}*\p{Pd}+\p{Z}*(.*)$"
        ),
        "trailing_space": regex.compile("\p{Z}*$"),
        "trailing_punct": regex.compile("[\p{Z}\p{P}]*$"),
        "non_breaking_space": regex.compile(" {2,}"),  # non-breaking space
        ".": regex.compile("\p{Z}*\.\p{Z}"),
        ",": regex.compile("\p{Z}*,\p{Z}*"),
        "final_dot": regex.compile("\s*\.\s*$"),
        "final_comma": regex.compile(",$"),
        # include rare errors like ".-—Blah" or ". -— Blah"
        "dot_n_dash": regex.compile("\p{Z}*[,.]\p{Z}*\p{Pd}+\p{Z}*"),
        "dot_opt_dash": regex.compile("\p{Z}*\.\p{Z}*\p{Pd}*\p{Z}*"),
        "comma_dash": regex.compile("\p{Z}*,\p{Z}*\p{Pd}\p{Z}*"),
        "colon": regex.compile("\p{Z}*:\p{Z}*"),
        "dash_and_more": regex.compile("(.*?)[.;:,]*\s*-*[-–—]\s*"),
        "colon_and_more": regex.compile("(.*?)\s*:\s*"),
        "didasc_and_more": regex.compile(".*?(?<!M)[.:]\s*"),
        # "char_no_dot": regex.compile("^\s*([A-Z1'-]+)\s*$"),
        # # using all 3 lengths: -, –, —, bc of inconsistencies
        # "char_dash": regex.compile("^\s*([A-Z1'-]{2,})\.[\s-]+[–—]\s"),
        # "char_comma_dash": regex.compile("^\s*([A-Z1'-]{2,},.*?)\.[\s-]+[–—]\s"),
        # "char_dot_more": regex.compile("^\s*([A-Z1'-]{2,}\.)(.*)$"),
        # "char_no_dot_more": regex.compile("^\s*([A-Z1'-]{2,})(.*)$"),
        "WORD": regex.compile("\p{Lu}{2,}"),
        "WORD_INIT": regex.compile("^(?:\p{Lu}[.']\p{Z}*)*[\p{Lu}\p{Pd}]{2,}"),
        "CHAR_ONELINE": regex.compile("^\p{Lu}+[\p{Z}\p{P}]*$"),
        "CHAR_ONELINE_DOT": regex.compile("^\p{Lu}+\p{Z}*\.\p{Z}*$"),
        "CHAR_ONELINE_COLON": regex.compile("^\p{Lu}+\p{Z}*:\p{Z}*$"),
        "INIT_char_DOT_n_DASH": regex.compile("^\p{L}+\.\p{Z}+\p{Pd}"),
        "INIT_char_COLON": regex.compile("^\p{L}+\p{Z}+:"),
        "INIT_CHAR_DOT_N_DASH": regex.compile("^\p{Lu}+\.\p{Z}+\p{Pd}"),
        "INIT_CHAR_COLON": regex.compile("^\p{Lu}+\p{Z}+:"),
        "init_char_dot_n_dash": regex.compile("^\p{Lu}+\p{Ll}+\.\p{Z}+\p{Pd}"),
        "init_char_colon": regex.compile("^(\p{Lu}\p{Ll}+)\p{Z}*:\p{Z}*"),
        "init_char_dash_nodot": regex.compile(
            "^(\p{Lu}['.]\p{Z}*)*[\p{Lu}\p{Z}]+\(.*?\)*\p{Z}*—"
        ),
        # single file with "A. or B. as characters: count-3202657-De_la_liberte.txt"
        "LETTER_CHARS": regex.compile("^(\p{Lu}\.)\p{Z}\p{Pd}\p{Z}"),
        # ----------------------------
        # regices for innards cleaning
        # ----------------------------
        # letters & space, possibly a parenthesis, : or — at the end
        "char_colon_or_dash": regex.compile(
            "^((?:\p{Lu}[,']\p{Z}*)*"
            + "[\p{L}\p{Pd}\p{Z}]+)"
            + "(\p{Z}\(.*?\))*"
            + "\p{Z}[:—]\p{Z}"
        ),
        # letters & space, possibly a parenthesis, : or — at the end
        "char_colon_or_dash_paren": regex.compile(
            "^((?:\p{Lu}[,']\p{Z}*)*"
            + "[\p{L}\p{Pd}\p{Z}]+)"
            + "(\p{Z}\(.*?\))*"
            + "\p{Z}[:—]\p{Z}"
        ),
        # lower case character, optionally with didasc, ending in dot and dash,
        "char_lc_dot_dash": regex.compile(
            "^([\p{Ll}\p{Z}]+)" + "(([,\p{Z}].*?)*)" + "\.\p{Z}*\p{Pd}\p{Z}*"
        ),
        # char (with numbers & spaces) followed or not by :
        "char_oneline_colon": regex.compile("^((L')*[\p{L}\p{N}\p{Z}]+?)\p{Z}*:$"),
        "char_colon": regex.compile("^(\p{L}{2,})\p{Z}*:\p{Z}*"),
        # "char_colon_more": regex.compile("^\s*([A-Z1'-]{2,})\s*:\s*(.*)$"),
        # line cleanup
        "(footnote)": regex.compile("\(\d+\)"),
        "sc_ene": regex.compile("SC\p{Z}+[EÈ]NE", regex.IGNORECASE),
        "deuxi_eme": regex.compile("DEUXI\p{Z}ÈME", regex.IGNORECASE),
    }


def index_of_regex_match(lines, r, trim=True):
    lines_len = len(lines)
    ind = 0
    found = False
    for i, l in enumerate(lines):
        if found:
            break
        if regex.search(r, l):
            found = True
            k = 1
            if trim:
                while i + k < lines_len and regex.match(R["blank_line"], lines[i + k]):
                    k += 1
            ind = i + k
            break
    return ind


# ----------------------------------------
# data pipelines


def get_all_data(fnames, n_files, txt_dir, trim_dir, load=False):
    D = {}
    for i, f in enumerate(fnames):
        if load:
            print(f"{i+1:4}/{n_files} | loading: {trim_dir}/{f}")
            D[f] = get_data(f, le_dir=txt_dir, trim=True, trim_dir=trim_dir)
        else:
            print(f"{i+1:4}/{n_files} | trimming & writing: {txt_dir}/{f}")
            D[f] = get_data(f, le_dir=txt_dir)
            save_lines(f, D[f]["trimmed"], le_dir=trim_dir)
    separator_print()
    if load:
        underprint(f"finished loading from {trim_dir}/")
    else:
        underprint(f"finished loading from {txt_dir} & trimming saved to {trim_dir}/")
    return D


def get_data(f, le_dir, trim=True, trim_dir="trimmed"):
    raw, lines, lines_len = get_lines(f, le_dir=le_dir)
    data = {
        "fname": f,
        "raw": raw,
        "lines": lines,
        "lines_len": lines_len,
    }
    if trim:
        trimmed, indices = trim_lines(f, lines, lines_len)
        trimmed_len = len(trimmed)
        data.update({"trimmed": trimmed, "trimmed_len": trimmed_len})
        data.update(indices)
    else:
        _, trimmed, trimmed_len = get_lines(f, le_dir=trim_dir)
        data.update({"trimmed": trimmed, "trimmed_len": trimmed_len})
    return data


def trim_lines(fname, lines, lines_len):
    author_index = find_author(fname, lines, lines_len)
    if not author_index:
        author_index = index_of_regex_match(lines, R["additional_author"])
    char_index = find_characters(fname, lines, lines_len)
    end_index = find_end(fname, lines, lines_len)
    start_index = max(author_index, char_index)
    return (
        lines[start_index:end_index],
        {
            "char_index": char_index,
            "author_index": author_index,
            "end_index": end_index,
            "start_index": start_index,
        },
    )


# ----------------------------------------
# trimming character, author, end


def find_characters(fname, lines, lines_len):
    feydeau = False  # almost all Feydeau files have 2-3 blocks of char
    vega = False  # Vega files can be cut up to line "La scène..."

    char_index = 0
    found_char = False
    limit = 15

    if fname in (
        "count-1537913-LES_ESPAGNOLS_EN_DANEMARK.txt",
        "count-1712853-LE_VERITABLE_SAINT_GENEST.txt",
        "count-3263112-LA_MORT_DE_WALLENSTEIN.txt",
        "count-2267304-LAmour_medecin.txt",
        "count-2037607-LHabit_vert.txt",
        "count-2158361-ANDROMEDE.txt",
        "count-3109664-SYLVANIRE.txt" "count-3397657-LA_VEINE.txt",
        "count-2047890-LE_ROI.txt",
        "count-3031455-Nono.txt",
    ):
        feydeau = True

    # have a long prologue
    if fname in ("count-1355612-UNE_FEMME_EST_UN_DIABLE.txt"):
        limit = 27

    for j, l in enumerate(lines[:limit]):
        if found_char:
            break
        if "Feydeau" in l and fname not in (
            "count-2199212-Les_Paves_de_lours.txt",
            "count-2316496-On_va_faire_la_cocotte.txt",
        ):
            feydeau = True
        if "Lope de Vega" in l:
            vega = True
        if regex.match(R["character"], l):
            found_char = True
            k = 1
            # files with space after char > k + 1
            if fname in (
                "count-1072543-CornPR.txt" "count-2158361-ANDROMEDE.txt",
                "count-2037607-LHabit_vert.txt",
                "count-1182649-LE_MONDE_OU_L.txt",
                "count-958980-Le_gendre_de_Monsieur_Poirier_-_Emile_Augier.txt",
                "count-1037209-LES_MAMELLES_DE_TIRESIAS_-_Guillaume_Apollinaire.txt",
            ):
                k += 1
            # more annoying exceptions
            if fname in ("count-959005-LOrphelin_de_la_Chine_-_Voltaire.txt",):
                # find init caps words only, no space (lest we go to the end)
                while j + k < lines_len and regex.match(R["WORD"], lines[j + k]):
                    k += 1
            elif vega:
                # all vega can go up to "La scène"
                while j + k < lines_len and not regex.match(
                    R["la_scene"], lines[j + k]
                ):
                    k += 1
            else:
                k = end_of_block_and_trim(lines, lines_len, j, k)
                # annoying exceptions: more chars after blank line
                if feydeau:
                    k = end_of_block_and_trim(lines, lines_len, j, k)
                    # some files like Feydeau with three !
                    if fname in (
                        "count-1537913-LES_ESPAGNOLS_EN_DANEMARK.txt",
                        "count-3263112-LA_MORT_DE_WALLENSTEIN.txt",
                        "count-2267304-LAmour_medecin.txt",
                        "count-3397657-LA_VEINE.txt",
                    ):
                        k = end_of_block_and_trim(lines, lines_len, j, k)
            char_index = j + k
    return char_index


def end_of_block_and_trim(lines, lines_len, j, k):
    # find end of block
    while j + k < lines_len and not regex.match(R["blank_line"], lines[j + k]):
        k += 1
    # trim empty lines
    while j + k < lines_len and regex.match(R["blank_line"], lines[j + k]):
        k += 1
    return k


def find_author(fname, lines, lines_len):
    author_index = 0
    found_author = False
    for j, l in enumerate(lines[:10]):
        if found_author:
            break
        if regex.match(R["author"], lines[j]):
            found_author = True
            # annoying exceptions
            if fname in (
                "count-1049195-Arret_36_de_lautobus_40_-_Jean_Sibil.txt",
                "count-1396213-Roberto_Succo.txt",
            ):
                k = 1
            elif fname == "count-1541294-Olaf_loriginal.txt":
                k = 2
            else:
                k = 2  # we assume "de\n\nauthor"
                while j + k < lines_len and not regex.match(
                    R["blank_line"], lines[j + k]
                ):
                    k += 1
            author_index = j + k + 1
    return author_index


def find_end(fname, lines, lines_len):
    end_index = lines_len - 1
    found_end = False
    for j, l in enumerate(reversed(lines[-4:])):
        if found_end:
            break
        if regex.search(R["fin"], l):
            found_end = True
            end_index = end_index - j - 1
    return end_index


# ----------------------------------------
# printing


def print_test(*args, utf=True, off="\t"):
    for i, arg in enumerate(args):
        if utf:
            arg_utf8 = arg.encode("utf-8")
        if "\n" in arg:
            print(f"{off}{i}  {arg}", end="")
            if utf:
                print(f"{off}{i}  {arg_utf8}")
        else:
            print(f"{off}{i}  {arg}")
            if utf:
                print(f"{off}{i}  {arg_utf8}")
    print(off + "-" * 40)
    print()


def print_file_stats(fname, i, n_files, char_index, author_index, end_index):
    print(f"file:     {fname}")
    print(f"no:       {i}/{n_files}")
    print(f"end char: {char_index}")
    print(f"end auth: {author_index}")
    print(f"end:      {end_index}")
    print()


def print_lines(lines):
    print("\n".join(lines))


def separator_print(offset=None):
    sep = "-" * 40
    if offset:
        sep = offset + sep
    print(sep)
    print()


def underprint(x):
    print(x)
    print("-" * len(x))


# ----------------------------------------
# files


def save_lines(f, lines, le_dir, clean=False):
    check_create_dir(le_dir, clean=clean)
    with open(os.path.join(le_dir, f), "w") as o:
        o.write("\n".join(lines))


def get_lines(input_name, le_dir):
    with open(
        os.path.join(le_dir, input_name), "r", encoding="utf-8", errors="ignore"
    ) as f:
        raw = f.read()
        lines = [l.strip() for l in raw.split("\n")]
    return raw, lines, len(lines)


def get_fnames(le_dir):
    if os.path.isdir(le_dir):
        fnames = [
            x for x in os.listdir(le_dir) if ".txt" == os.path.splitext(x)[-1]
        ]  # don't load vim *.swp files
        n_files = len(fnames)
        print(f"found {n_files} files in directory: {le_dir}")
        separator_print()
        return fnames, n_files
    else:
        print(f"{le_dir} directory not found.")


def check_create_dir(d, clean=False):
    if not os.path.isdir(d):
        os.mkdir(d)
    if clean:
        [os.remove(os.path.join(d, f)) for f in os.listdir(d)]

#----------------------------------------
# other utils

def binary_insert(lst, el):
    if not lst:
        return [el]
    half = len(lst)//2
    lo = lst[:half]
    hi = lst[half:]
    if el[1] > hi[0][1]:
        if len(hi) > 1:
            hi = binary_insert(hi, el)
        else:
            return hi + [el]
    elif lo and el[1] < lo[-1][1]:
        lo = binary_insert(lo, el)
    else:
        return lo + [el] + hi
    return lo + hi

if __name__ == "__main__":

    R = make_regices()

    try:
        main()
    except KeyboardInterrupt:
        print("keyboard interrupt")
