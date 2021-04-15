# Scraping [Théatre gratuit](https://theatregratuit.com/)

Using Python 3, [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) and [regex](https://pypi.org/project/regex/).

```bash
$ python scrape.py
$ python extract.py
$ python dataset.py
```

The first script will produce the folder `theatregratuit-epubs`, containing all
the scraped epubs.

The second one will extract the epubs to plain text files, or just transfer the
plain text files, to the folder `theatregratuit-txt`.

The third will follow the following steps:
 - attempt to trim the files from unwanted beginnings and ends, placing them
   into `trimmed`;
 - attempt a first processing pass, saving the files to `formatted`, the rest
   to `rest`;
 - attempt a second processing pass of `rest`;
 - copying all files to `theatregratuit-dataset`.

The result is the removal of introductory contents (character lists for
instance), and surrounding each theatre lines (one character speaking, possible
didascalia, and the text) with the markers `<|s|>` and `<|e|>`, that will be
used to identify these points when training a neural net on it.

The scripts will first check whether files are present, and skip them. For a
re-download or re-processing, erase the files or directories first.

In order to speed up reruns when working on the scripts, `dataset.py` produces
two hidden pickled files `.DATA.pkl` and `.FORMATTED.pkl`, that allows the
script to reload intermediary steps and speed up the process (delete the files
if you need that process to be executed again).
