I use this script to schedule my jazz piano practice according to the approach described [here](https://malcolmsailor.com/2023/11/22/anki-for-jazz-practice.html). Of course, you could use it to practice anything.

# Usage

After installing the requirements and creating a folder for your practice decks and cards, you can see the cards that are due with the following command. (Of course, there will not be any cards due until you create some yourself.)

```bash
python practice_scheduler.py path/to/folder
```

If you're going to use the script to practice, you'll need to invoke it frequently, so it will be more practical to assign an alias to it. For instance, I have the following alias for `pj` (= "practice jazz") in my `.bashrc`:

```bash
alias pj="python path/to/practice_scheduler.py path/to/my/practice/folder"
```

To add a deck, you can then do

```bash
python practice_scheduler.py path/to/folder --add-deck "my deck"
```

To add a card to an existing deck, you can do
```bash
python practice_scheduler.py path/to/folder --add "my deck" "card name"
```

Using my alias, these commands become:

```bash
pj --add-deck "my deck"
pj --add "my deck" "card name"
```

For a full list of options, invoke the script with `--help`.


# Technical notes

I wrote it very quickly and hackily for my personal usage. Rather than using some sort of database it simply uses the file system, storing decks as folders and cards as YAML files. While this probably isn't the sleekest implementation, it has the advantage of making the cards very easy to edit manually. Undo was also very easy to implement by maintaining the folder as a Git repository.
