import os
import bs4
import regex
import shutil
import zipfile
from bs4 import BeautifulSoup


def main():
    txt_dir = "theatregratuit-txt"
    if os.path.isdir(txt_dir):
        fnames = [x for x in os.listdir(txt_dir) if ".txt" == os.path.splitext(x)[-1]]
        n_files = len(fnames)
        print(f"found {n_files} files in directory: {txt_dir}")
    else:
        print(
            f"{txt_dir} directory not found, please run epub_to_txt.py first, and scrape.py if the epubs have not been downloaded"
        )
    separator_print()

    tmp_dir = "tmp1"
    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    # ds_dir = "theatregratuit-dataset"
    # if not os.path.isdir(ds_dir):
    #     os.mkdir(ds_dir)

    regices = make_regices()
    off = "\t"

    # for later: instead load the full file and use regices?
    # (especially as some files have multiple PERSONNAGES lists)
    for i, fname in enumerate(fnames):

        print(f"{i:4}/{n_files} | {fname}")

        with open(
            os.path.join(txt_dir, fname), "r", encoding="utf-8", errors="ignore"
        ) as f:
            raw = f.read()

        # chars_block_it =  regex.finditer(regices["characters_block"], raw)
        # found = 0
        # blocks = []
        # for chars_block in chars_block_it:
        #     if chars_block:
        #         found += 1
        #         # annoying exceptions: when the regex catches an entire block of play
        #         if len(chars_block.group(0)) < 6000:
        #             raw = regex.sub(regex.escape(chars_block.group(0)), "", raw)
        #             blocks.append(chars_block.group(0))

        # if found:
        #     print(fname)
        #     for b in blocks:
        #         print(b)
        #     print('-'*40)
        #     print()

        lines = raw.split('\n')
        lines_len = len(lines)

        char_index = find_characters(fname, lines, lines_len, regices, off)

        # chars always come after author, no need to check for that if found
        if char_index == 0:
            author_index = find_author(fname, lines, lines_len, regices, off)
        else:
            author_index = char_index
        # author_index = find_author(fname, lines, lines_len, regices, off)

        # end business
        end_index = find_end(fname, lines, lines_len, regices, off)

        # print_file_stats(fname, i, n_files, char_index, author_index, end_index)

        ## checks
        ##-------
        ## neither char nor author found, check
        # if author_index == 0:
        #    print(f"{off}*** no characters nor author found")
        #    print()
        #    for l in lines[author_index : author_index + 10]:
        #        print(f"{off}{l}", end="")
        #    separator_print(offset=off)

        # if end_index == lines_len - 1:
        #    print(f"{off}*** no end found")
        #    print()
        #    for l in lines[end_index-3:]:
        #        print(f"{off}{l}", end="") if '\n' in l else print(f"{off}{l}")
        #    separator_print(offset=off)

        # formatting & markers
        # ---------------------


        # trimmed = ''.join(lines[author_index:end_index]).strip()
        # if regex.search(regices["dash"], trimmed):
        #     with open(os.path.join(tmp_dirs[0], fname), 'w') as o:
        #         o.write(regex.sub(regices["dash"], ".\n", trimmed))
        # else:
        #     with open(os.path.join(tmp_dirs[1], fname), 'w') as o:
        #         o.write(trimmed)

        new_lines = []
        for j, l in enumerate(lines[author_index:end_index]):

            # remove end trailing space, replace multiple annoying spaces by one
            l =  l.strip() + "\n"
            l = regex.sub(regices["non_breaking_space"], " ", l)

            # check for full caps line
            caps_full_re = regex.match(regices["caps_full"], l)
            if caps_full_re:
                # check for final punctuation (should always succeed)
                trail_re = regex.search(regices["trailing_punct"], l)
                if trail_re:
                    new_l = l[:trail_re.span()[0]] + ".\n"
                    # print_test(l, new_l)
                    new_lines.append("<|e|>\n")
                    new_lines.append("<|s|>\n")
                    new_lines.append(new_l)
                continue

            # check for initial series of caps words (characters)
            caps_init_re = regex.match(regices["caps_init"], l)
            # check for annoying beginnings (M. , or L' )
            annoying_re = regex.match(regices["annoying_init"], l)
            if annoying_re:
                caps_init_re = regex.match(regices["caps_init"], l[annoying_re.span()[1]:])


            # if a character in caps detected at beginning of line
            if caps_init_re:

                caps_init_end_index = caps_init_re.span()[1]
                caps_init_start = l[:caps_init_end_index]
                caps_init_rest = l[caps_init_end_index:]

                new_lines.append("<|e|>\n")
                new_lines.append("<|s|>\n")
                new_lines.append(l)
                continue

            char_lc_dot_dash_re = regex.match(regices["char_lc_dot_dash"], l)

            if char_lc_dot_dash_re:
                new_lines.append("<|e|>\n")
                new_lines.append("<|s|>\n")
                char = char_lc_dot_dash_re.group(1) + "\n"
                rest = char_lc_dot_dash_re.group(2) + "\n"
                new_lines.append(char.upper())
                new_lines.append(rest)
                continue


            new_lines.append(l)


        new_lines.append("<|e|>")

        with open(os.path.join(tmp_dir, fname), 'w') as o:
            o.writelines(new_lines)

                # print_test(l, caps_init_start, caps_init_rest)
                # continue

                # # is there a dash on the line?
                # dash_re = regex.match(regices["dash_and_more"], caps_init_rest)
                # if dash_re:
                #     end_dash = dash_re.span()[1]
                #     dashless = caps_init_start + dash_re.group(1) + "."
                #     rest = caps_init_rest[end_dash:]
                #     # print_test(l, dashless, rest)
                #     new_lines.append(dashless + "\n")
                #     new_lines.append(rest)
                #     continue

                # is there a colon on the line?
                # colon_re = regex.match(regices["colon_and_more"], caps_init_rest)
                # if colon_re:
                #     end_colon = colon_re.span()[1]
                #     colonless = caps_init_start + colon_re.group(1) + "."
                #     rest = caps_init_rest[end_colon:]
                #     # print_test(l, caps_init_start, caps_init_rest)
                #     # print_test(l, colonless, rest, utf=False)
                #     new_lines.append(colonless + "\n")
                #     new_lines.append(rest)
                #     continue

                # # is there more all-caps words after caps init?
                # more_caps_w_re = regex.finditer(regices["caps_word"], caps_init_rest)
                # # Find the last one.
                # # https://stackoverflow.com/a/2988680
                # for last_caps_w in more_caps_w_re:
                #     # print(f"{off}:      {last_caps_w}")
                #     pass
                # if last_caps_w:
                #     more_caps = caps_init_start + caps_init_rest[:last_caps_w.span()[1]]
                #     more_caps_rest = caps_init_rest[last_caps_w.span()[1]:]
                #     # print_test(l, caps_init_start, more_caps, more_caps_rest, repr(last_caps_w))
                #     # print_test(l, more_caps, more_caps_rest)
                #     more_caps_w_re, last_caps_w = None, None
                #     # continue

                # print_test(l, caps_init_start, caps_init_rest)

                # if the rest is empty
                # # blank_rest_re = regex.match(regices["blank_line"], caps_init_rest)
                # blank_rest_re = regex.search(regices["blank_line_with_rubbish"], caps_init_rest)
                # if blank_rest_re:
                #     # print_test(l, caps_init_start, caps_init_rest)

                    # punct_re = regex.search(regices["trailing_punct"], caps_init_rest)
                    # regex always succeeds as just space will have been caught
                    # as a full caps line above
                    # punctless = caps_init_start[:punct_re.span()[0]]
                    # punct_rest = caps_init_start[punct_re.span()[0]:]
                    # # new_lines.append(punctless + ".\n")
                    # # print_test(l, punctless, punct_rest)
                    # continue
                # else:
                    # # print_test(l, caps_init_start, caps_init_rest)
                    # continue

                # print_test(l, caps_init_start, caps_init_rest)
                # continue

                # # case: init caps ending with "."
                # dot_re = regex.search(regices["final_dot"], caps_init_start)
                # if dot_re:
                #     # print_test(l, caps_init_start, caps_init_rest)
                #     if regex.match(regices["M."], caps_init_start):
                #         # print_test(l, caps_init_start, caps_init_rest)
                #         continue
                #     else:
                #         # print_test(l, caps_init_start, caps_init_rest)
                #         continue

                    # # append character + .
                    # pre_dot = l[:dot_re.span()[0]] + "."
                    # # print_test(l, pre_dot, post_dot)
                    # new_lines.append(pre_dot)
                    # rest_re = regex.match(regices["blank_line"], caps_init_rest[dot_re.span()[1]:])
                    # # if not blank after check for dash
                    # if not rest_re:
                    #     post_dot = caps_init_rest[dot_re.span()[1]:]
                    #     # print_test(l, pre_dot, post_dot)
                    #     new_lines.append(post_dot)
                    # else:
                    #     # print_test(l, post_dot)
                    #     pass
                    # continue

                # # case: caps char followed by ","
                # comma_re = regex.search(regices["final_comma"], caps_init_start)
                # if comma_re:
                #     continue
                # #     didasc_re = regex.match(regices["didasc_and_more"], caps_init_rest[1:])
                # #     if didasc_re:
                # #         didasc_end = didasc_re.span()[1]
                # #         new_lines.append(l[:caps_init_end_index+didasc_end+1] + "\n")
                # #         lll = caps_init_rest[1+didasc_end:]
                # #         blank_re = regex.match(regices["blank_line"], lll)
                # #         if not blank_re:
                # #             # print_test(l, l[:caps_init_end_index+didasc_end+1], lll)
                # #             new_lines.append(lll)
                # #             continue
                # #         else:
                # #             # print_test(l, l[:caps_init_end_index+didasc_end+1])
                # #             continue

                # case: caps char followed by ":"
                # colon_re = regex.match(regices["colon_and_more"], caps_init_rest)
                # if colon_re:
                #     end_colon = colon_re.span()[1]
                #     colonless = caps_init_start + colon_re.group(1) + "."
                #     rest = caps_init_rest[end_colon:]
                #     print_test(l, colonless, rest)
                #     new_lines.append(colonless + "\n")
                #     new_lines.append(rest)
                #     continue

                # else:
                #     continue

                # # check for comma and more (other char, didascalia)
                # n = regex.match(regices["didasc_and_more"], caps_init_rest)
                # if n:
                #     end_n = n.span()[1]
                #     lll = caps_init_rest[end_n:]

                    # if lll:
                    #     print_file_stats(fname, i, n_files, char_index, author_index, end_index)
                    #     print(f"{off}old:  {l}", end="")
                    #     print(f"{off}new:  {l[:caps_init_end_index+end_n]}")
                    #     print(f"{off}rest: {lll}", end="")
                    #     print()
                    # continue
                # else:
                    # print_file_stats(fname, i, n_files, char_index, author_index, end_index)
                    # print(f"{off}old:  {l}", end="")
                    # print(f"{off}new:  {caps_init_start}")
                    # print(f"{off}rest: {caps_init_rest}", end="")
                    # print()
                    # continue

                # case: dot
                # case: comma

            # else:
            #     continue

            # m = regex.match(regices["char_no_dot"], l)
            # if m:
            #     replaced = True
            #     new_l = m.group(1) + ".\n"
            #     new_lines.append(new_l)
            #     # print(f"{off}old: {l}", end="")
            #     # print(f"{off}new: {new_l}", end="")
            #     # print()
            #     continue

            # m = regex.match(regices["char_dash"], l)
            # if m:
            #     replaced = True
            #     new_l = m.group(1) + ".\n"
            #     rest_l = l[m.span()[1] :]
            #     new_lines.append(new_l)
            #     # print(f"{off}old:  {l}", end="")
            #     # print(f"{off}new:  {new_l}", end="")
            #     if rest_l:
            #         # print(f"{off}rest: {rest_l}", end="")
            #         new_lines.append(rest_l)
            #     # print()
            #     continue

            # m = regex.match(regices["char_comma_dash"], l)
            # if m:
            #     replaced = True
            #     new_l = m.group(1) + ".\n"
            #     rest_l = l[m.span()[1] :]
            #     new_lines.append(new_l)
            #     # print(f"{off}old:  {l}", end="")
            #     # print(f"{off}new:  {new_l}", end="")
            #     if rest_l:
            #         # print(f"{off}rest: {rest_l}", end="")
            #         new_lines.append(rest_l)
            #     # print()
            #     continue

            # m = regex.match(regices["char_colon"], l)
            # if m:
            #     replaced = True
            #     new_l = m.group(1) + ".\n"
            #     new_lines.append(new_l)

                # print_file_stats(fname, i, n_files, char_index, author_index, end_index)
                # print(f"{off}old: {l}", end="")
                # print(f"{off}new: {new_l}", end="")
                # print()

                # continue

            # m = regex.match(regices["char_comma_dash"], l)
            # if m:
            #     replaced = True
            #     new_l = m.group(1) + ".\n"
            #     rest_l = l[m.span()[1] :]
            #     new_lines.append(new_l)
            #     # print(f"{off}old:  {l}", end="")
            #     # print(f"{off}new:  {new_l}", end="")
            #     if rest_l:
            #         # print(f"{off}rest: {rest_l}", end="")
            #         new_lines.append(rest_l)
            #     # print()
            #     continue

            # m = regex.match(regices["char_dot_more"], l)
            # if m:
            #     replaced = True
            #     new_l = m.group(1) + "\n"
            #     rest_l = l[m.span()[1] :]
            #     new_lines.append(new_l)
            #     print(f"{off}old:  {l}", end="")
            #     print(f"{off}new:  {new_l}", end="")
            #     if rest_l:
            #         print(f"{off}rest: {rest_l}", end="")
            #         new_lines.append(rest_l)
            #     print()
            #     continue

            # new_lines.append(l)

        # separator_print(offset=off)

    # for tmp_dir in tmp_dirs:
    #     shutil.rmtree(tmp_dir)


def make_regices():
    return {
        "blank_line": regex.compile("^\s*$"),
        "blank_line_with_rubbish": regex.compile("^[\p{Z}\p{P}]*$"),
        "character": regex.compile(
            "^\s*((les )*pe*rsonna *ge|(les )*acteurs|dramatis personae|entreparleur|biographies|apparences|personrage|persongueules|pépersonâge)",
            regex.IGNORECASE,
        ),
        "characters_block": regex.compile("\n*\s*PERSONNAGES?(.*?)(\n\s*\n)+", regex.DOTALL),
        "author": regex.compile("(^\s*de\s*$|^\(Auteur inconnu\))", regex.IGNORECASE),
        "fin": regex.compile("(fin|rideau|f1n|inachev|manque)", regex.IGNORECASE),
        # search for lines made of full caps + punct/space, as well as some
        # very common words listing characters, and didascalia in ()
        "caps_full": regex.compile("^\s*((\p{Lu}+|seule?|puis|puis tout le monde|moins|et)\s*[.’'<>;,]*\s*)+\s*(\(.*?\))*\s*$"),
        # common annoying starts "M.", "L'"
        "annoying_init": regex.compile("^[\p{P}\p{Z}]*(M\.|\p{Lu}')\p{Z}*"),
        # words (with possible - or '), and space, with punctuation at the end
        "caps_init": regex.compile("^\s*(([\p{Lu}\p{Pc}\p{Pd}1]+\p{Zs}*)+)(\s*[\p{Po}]\s*)"),
        "char_lc_dot_dash": regex.compile("^(\p{Z}*M*[\p{Ll}\p{Z}]+\.)\p{Z}*\p{Pd}+\p{Z}*(.*)$"),
        "caps_word": regex.compile("\p{Lu}{2,}"),
        "trailing_space": regex.compile("\s*$"),
        "trailing_punct": regex.compile("\s*[.,:]*\s+$"),
        "non_breaking_space": regex.compile(" {2,}"), # non-breaking space
        "M." : regex.compile("M.\s"),
        "dot": regex.compile("\s*\.\s*"),
        "final_dot": regex.compile("\s*\.\s*$"),
        "final_comma": regex.compile(",$"),
        # include rare errors like ".-—Blah" or ". -— Blah"
        "dash": regex.compile("[,.](\s*[-–—]+|-[–—])\s*"),
        "dash_and_more": regex.compile("(.*?)[.;:,]*\s*-*[-–—]\s*"),
        "colon": regex.compile("\s*:\s*"),
        "colon_and_more": regex.compile("(.*?)\s*:\s*"),
        "didasc_and_more": regex.compile(".*?(?<!M)[.:]\s*"),
        # "char_no_dot": regex.compile("^\s*([A-Z1'-]+)\s*$"),
        # # using all 3 lengths: -, –, —, bc of inconsistencies
        # "char_dash": regex.compile("^\s*([A-Z1'-]{2,})\.[\s-]+[–—]\s"),
        # "char_comma_dash": regex.compile("^\s*([A-Z1'-]{2,},.*?)\.[\s-]+[–—]\s"),
        # "char_dot_more": regex.compile("^\s*([A-Z1'-]{2,}\.)(.*)$"),
        # "char_no_dot_more": regex.compile("^\s*([A-Z1'-]{2,})(.*)$"),
        # "char_colon": regex.compile("^\s*([A-Z1'-]{2,})\s*:\s*$"),
        # "char_colon_more": regex.compile("^\s*([A-Z1'-]{2,})\s*:\s*(.*)$"),
    }


def find_end(fname, lines, lines_len, regices, off):
    end_index = lines_len - 1
    found_end = False
    for j, l in enumerate(reversed(lines[-4:])):

        if found_end:
            break

        if regex.search(regices["fin"], l):
            found_end = True
            end_index = end_index - j - 1

    return end_index


def find_author(fname, lines, lines_len, regices, off):
    author_index = 0
    found_author = False
    for j, l in enumerate(lines[:10]):

        if found_author:
            break

        if regex.match(regices["author"], lines[j]):
            found_author = True
            k = 2  # we assume "de\n\nauthor"
            while j + k < lines_len and not regex.match(
                regices["blank_line"], lines[j + k]
            ):
                k += 1
            author_index = j + k + 1

    return author_index


def find_characters(fname, lines, lines_len, regices, off):
    char_index = 0
    found_char = False
    for j, l in enumerate(lines):

        if found_char:
            break

        if regex.match(regices["character"], l):

            # print(f"{off}found character list in file: {fname}")
            # print()
            # print(f"{off}{l}")

            found_char = True
            k = 1
            while j + k < lines_len and not regex.match(
                regices["blank_line"], lines[j + k]
            ):
                k += 1

            char_index = j + k + 1

            # for ll in lines[j+1:j+k+1]:
            #     print(f"{off}{ll}", end="")
            # separator_print(offset=off)
            # print()

        # if not found_char:
        #     print(f"{off}nothing in: {fname}")
        #     print()
        #     for j, l in enumerate(lines):
        #         if j > 10:
        #             break
        #         print(f"{off}{l}", end="")
        #     separator_print(offset=off)
        #     print()

    return char_index

def print_test(*args, utf=True, off="\t"):
    for i, arg in enumerate(args):
        if utf: arg_utf8 = arg.encode('utf-8')
        if '\n' in arg:
            print(f"{off}{i}  {arg}", end="")
            if utf: print(f"{off}{i}  {arg_utf8}")
        else:
            print(f"{off}{i}  {arg}")
            if utf: print(f"{off}{i}  {arg_utf8}")
    print(off + "-"*40)
    print()

def print_file_stats(fname, i, n_files, char_index, author_index, end_index):
    print(f"file:     {fname}")
    print(f"no:       {i}/{n_files}")
    print(f"end char: {char_index}")
    print(f"end auth: {author_index}")
    print(f"end:      {end_index}")
    print()

def separator_print(offset=None):
    sep = "-" * 40
    if offset:
        sep = offset + sep
    print(sep)
    print()


# remove title & author:
# 1) use character to jump beyond them
# 2) if no chars ?

# remove character list:
# personages
# entreparleurs
# dramatis personae
# idiosyncrasies & typos

# reformat characters to uppercase and single line:
# remove full stop
# "–"

# add markers

# remove ending:
# FIN(.)
# RIDEAU(.)
# idiosyncrasies

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('keyboard interrupt')
