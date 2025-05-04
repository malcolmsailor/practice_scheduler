I use this script to schedule my jazz piano practice according to the approach described [here](https://malcolmsailor.com/2023/11/22/anki-for-jazz-practice.html). Of course, you could use it to practice anything.

Example output:

```
    Deck         N due    N new  Top card                                Hard    Good    Easy
--  ---------  -------  -------  --------------------------------------  ------  ------  ------
 1  Tunes            6        0  Im old fashioned                        5d      10d     20d
 2  Harmony          1        1  Keep harmonies as diatonic as possible  1d      3d      6d
 3  Rhythm           8        1  Constant triplets in RH with metronome  6d      12d     24d
 4  LHTexture        5        1  Octave-shell voicings oom-pah           1d      3d      6d
```

# Basic usage

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

# View upcoming cards

On 2025/05/04, I added a second script to this folder to print the upcoming cards in a nice format. The basic invocation is as follows:

```bash
python view_upcoming.py path/to/folder
```

There are a few options which can be seen by invoking the script with the `--help` flag.

# Technical notes

I wrote this script very quickly and hackily for my personal usage. Rather than using some sort of database it simply uses the file system, storing decks as folders and cards as YAML files. While this probably isn't the sleekest implementation, it has the advantage of making the cards very easy to edit manually. Undo was also very easy to implement by maintaining the folder as a Git repository.
