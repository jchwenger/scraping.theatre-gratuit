import os
import bs4
import regex
import shutil
import zipfile
from bs4 import BeautifulSoup

def main():
    in_dir = "theatregratuit-epubs"
    if os.path.isdir(in_dir):
        fnames = os.listdir(in_dir)
        n_files = len(fnames)
        print(f"found {n_files} files in directory: {in_dir}")
    else:
        print(f"{in_dir} directory not found, please run scrape.py first")

    # https://stackoverflow.com/a/39474567
    html_re = regex.compile('^(?!.*titlepage).*\.x*html', regex.IGNORECASE)

    tmp_dir = "tmp"
    if not os.path.isdir(tmp_dir):
        os.mkdir(tmp_dir)

    txt_dir = 'theatregratuit-txt'
    if not os.path.isdir(txt_dir):
        os.mkdir(txt_dir)

    off = "\t"

    for i, f in enumerate(fnames):

        # if i > 0:
        #     break

        print(f"epub: {i}/{n_files} | {f}")
        print()

        txt_f = os.path.splitext(f)[0] + '.txt'
        out_name = os.path.join(txt_dir, txt_f)

        if not os.path.isfile(out_name):

            html_files = []
            # extracting one or more html files
            with zipfile.ZipFile(os.path.join(in_dir, f), 'r') as z:
                for o in z.infolist():
                    if regex.search(html_re, o.filename):
                        tmp_name = os.path.join(tmp_dir, o.filename)
                        print(f"{off}extracting: {o.filename}")
                        z.extract(o.filename, tmp_dir)
                        html_files.append(tmp_name)

            soups = []
            n_soups = 0
            for h in html_files:
                with open(h, 'r') as f:
                    soups.append(BeautifulSoup(f.read(), "html.parser"))
                    n_soups += 1

            for soup in soups:
                print(f"{off}writing to: {txt_f}")
                print()
                # https://stackoverflow.com/a/19760007
                [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
                visible_text = soup.getText().strip()
                with open(out_name, 'a') as o:
                    o.write(visible_text)
                    if n_soups > 1:
                        o.write('\n')
        else:
            print(f"{off}already processed {txt_f}")
            print()

    shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    main()
