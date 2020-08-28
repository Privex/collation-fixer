# Character Set (Charset) / Collation Mass Conversion Tool for MariaDB / MySQL databases, tables and columns

```
+===================================================+
|                 © 2020 Privex Inc.                |
|               https://www.privex.io               |
+===================================================+
|                                                   |
|        MariaDB/MySQL Charset/Collation Fixer      |
|        License: X11/MIT                           |
|                                                   |
|        Core Developer(s):                         |
|                                                   |
|          (+)  Chris (@someguy123) [Privex]        |
|          (+)  Kale (@kryogenic) [Privex]          |
|                                                   |
+===================================================+

MariaDB/MySQL Charset/Collation Fixer - A Python tool to painlessly convert 
MariaDB/MySQL databases, tables, and/or columns into different character sets 
and collations, most notably utf8mb4 + utf8mb4_unicode_ci

Copyright (c) 2020    Privex Inc. ( https://www.privex.io )
```

Many people have experienced issues with handling UTF-8 in their MySQL/MariaDB databases and tables before,
but due to the pain of manually converting every single table and every single column to UTF-8,
it's often either ignored, or only a partial conversion is done on important columns/tables.

This is because for a long time, the default character set of MySQL/MariaDB has been `latin1`,
with the `latin1_swedish_ci` collation - which supports only a very small subset of UTF-8.

Modern versions of MariaDB in some Linux distributions such as Ubuntu 20.04 - now have their default set to `utf8mb4`,
however this doesn't help people who are using an existing older database, or have their database/tables
created via a standard framework's database migration tool which still defaults to `latin1`.

Recently, a new SQL feature was added to `ALTER TABLE` to allow converting an entire table
and it's columns to a character set / collation:
 
```
ALTER TABLE [table] CONVERT TO CHARACTER SET [charset] COLLATE [collation]
```

Unfortunately, this still isn't very helpful if you have tables with foreign keys / certain indexes,
as the query will likely error, complaining about a conflict with converting the index.

This tool is designed to solve that issue, and make it much easier/faster to convert older databases
to UTF-8, safely, and without problems.

By default, the conversion charset is `utf8mb4` and the collation is `utf8mb4_unicode_ci`. This is
considered the "best" UTF-8 character set and collation to use, for reliably handling UTF-8
data in your tables.

It will also skip conversion of columns which either have an index (and may be unsafe to convert),
are already using the correct character set, OR don't require character sets (e.g. numeric and date types).

There are a variety of options available, allowing fine grained control over what gets converted:
 
 - You can convert just tables themselves (and not the columns)
 - You can convert columns themselves (and not their tables)
 - You can convert a single table and specific columns within it
    - You can convert all columns within a single table
 - Or you can use the nuclear option - `convert_tables -a -k` which converts **all tables** 
   and **all valid columns** within each table to the selected character set / collation 
   (default `utf8mb4` / `utf8mb4_unicode_ci` ) 

# Quickstart with Docker

```shell script
docker run --rm -it privex/colfixer -s host -u user -p pass -P 3306 -d dbname [sub_command] [arguments]
```

Example - using `list_tables` with `somedb` on the remote server `sql.example.com` and the user `dave`:

```
user@host ~ $ docker run --rm -it privex/colfixer -s sql.example.com -u dave -p SecurePass -d somedb list_tables

Table list for database: somedb 

+-----------------------------------------+-----------------------------------------+-----------------------------------------+
| Name                                    | Char Set                                | Collation                               |
+-----------------------------------------+-----------------------------------------+-----------------------------------------+
| t1                                      | utf8mb4                                 | utf8mb4_general_ci                      |
| t2                                      | utf8mb4                                 | utf8mb4_general_ci                      |
+-----------------------------------------+-----------------------------------------+-----------------------------------------+

```

Example - using `convert_tables` with connection details from a local .env file:

```
# First we'll create ~/db.env
user@host ~ $ cat > ~/db.env <<"EOF"
DB_HOST=192.168.4.38
DB_PORT=3306

DB_NAME=my_app
DB_USER=root
DB_PASS=MyS3cur3P4ss

EOF

# Now we convert ALL tables and their columns using `convert_tables -a -k`
user@host ~ $ docker run --rm --env-file ~/db.env -it privex/colfixer convert_tables -a -k
```

# Quickstart locally with Python

```shell script
apt update
# If you don't already have Python / aren't sure
apt install -y python3 python3-dev python3-pip
apt install -y python3-venv
# For Ubuntu 20.04 and Debian 10 - the latest Python available is already installed (3.8 for 20.04, 3.7 for deb 10)
# For Ubuntu 18.04 you should install Python 3.8, and for Debian 9, install 3.7
apt install -y python3.7
apt install -y python3.8
# You'll need libmariadbclient-dev or libmysqlclient-dev for the 'mysqlclient' 
# python library to work
apt install -y libmariadbclient-dev

# Install pipenv using the newest Python you have installed (For Ubuntu, up to 3.8, for Debian up to 3.7)
python3.8 -m pip install -U pipenv

# Clone the repo
git clone https://github.com/Privex/collation-fixer

cd collation-fixer

# Create a virtualenv + install Python dependencies using pipenv
# Use --ignore-pipfile to speed up the install
pipenv install --ignore-pipfile

# Enter the virtual env
pipenv shell

# Create a .env file and adjust it to point to your MariaDB/MySQL server
cp example.env .env
nano .env

# Start using collation-fixer :)
# Use -h or --help to show detailed help on how to use it
./app.py -h
```

# Requirements

 - Python 3.6 or newer
    - Python 3.7+ is recommended for this project to work best
    - If you're running this on Python 3.6.x - you'll need to install the backported
      `dataclasses` package with `pip3 install -U dataclasses` - as dataclasses were
      first added in Python 3.7

 - `libmariadbclient-dev` or `libmysqlclient-dev` - required for the `mysqlclient` library
 
 - Tested on Mac OSX 10.14 (Mojave) and Ubuntu Server 18.04 + 20.04 - may or may not work
   on Windows, BSDs, and other OS's.
   
    - Using [Docker](https://www.docker.com/get-started), you should be able to run this
      Python application on most major OS's without issues.
 
 - Access to a **MariaDB** or **MySQL** server. 
    - Depending on how your database/table permissions are setup, you may need to use the `root` user to be
      able to convert the character set / collation of tables and columns.


# License

This Python module was created by [Privex Inc. of Belize City](https://www.privex.io), and licensed under the X11/MIT License.
See the file [LICENSE](https://github.com/Privex/collation-fixer/blob/master/LICENSE) for the license text.

**TL;DR; license:**

We offer no warranty. You can copy it, modify it, use it in projects with a different license, and even in 
commercial (paid for) software.

The most important rule is - you **MUST** keep the original license text visible (see `LICENSE`) in any copies.


# Usage (examples)


```shell script
# Show tables in your configured database, including their charset + collation
./app.py list_tables

# Show ALL columns in ALL tables in your database
./app.py list_columns

# Show columns just for the table 'users'
./app.py list_columns users

# (Most common usage) Convert all tables and their columns to utf8mb4 + utf8mb4_unicode_ci
./app.py convert_tables -a -k

# Convert the single table 'users' and all of it's columns to utf8mb4 + utf8mb4_unicode_ci
./app.py convert_tables -k users

# Convert the single table 'users' (but not columns) to utf8mb4 + utf8mb4_unicode_ci
./app.py convert_tables users

# Convert the 'users' columns 'username' and 'email' to utf8mb4 + utf8mb4_unicode_ci
# Does not affect the table itself, or any other columns.
./app.py convert_columns users -c username email
 
```


# Contributing

We're happy to accept pull requests, no matter how small.

Please make sure any changes you make meet these basic requirements:

 - Any code taken from other projects should be compatible with the MIT License
 - This is a new project, and as such, supporting Python versions prior to 3.6 is very low priority.
 - However, we're happy to accept PRs to improve compatibility with older versions of Python, as long as it doesn't:
   - drastically increase the complexity of the code
   - OR cause problems for those on newer versions of Python.

**Legal Disclaimer for Contributions**

Nobody wants to read a long document filled with legal text, so we've summed up the important parts here.

If you contribute content that you've created/own to projects that are created/owned by Privex, such as code or 
documentation, then you might automatically grant us unrestricted usage of your content, regardless of the open source 
license that applies to our project.

If you don't want to grant us unlimited usage of your content, you should make sure to place your content
in a separate file, making sure that the license of your content is clearly displayed at the start of the file 
(e.g. code comments), or inside of it's containing folder (e.g. a file named LICENSE). 

You should let us know in your pull request or issue that you've included files which are licensed
separately, so that we can make sure there's no license conflicts that might stop us being able
to accept your contribution.

If you'd rather read the whole legal text, it should be included as `privex_contribution_agreement.txt`.


# Thanks for reading!

**If this project has helped you, consider [grabbing a VPS or Dedicated Server from Privex](https://www.privex.io).**

**Prices start at as little as US$0.99/mo (we take cryptocurrency!)**
