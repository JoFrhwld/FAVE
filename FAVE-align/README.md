# FAVE-align

* [Installation](#installation)
    * [Dependencies](#dependencies)
        * [HTK 3.4.1](#htk-341)
        * [sox](#sox)
* [Usage](#usage)

## Installation

### Dependencies

FAVE-align depends on HTK and sox to work. As such, you'll need to have these installed.

#### HTK 3.4.1
##### OS X
###### Command line tools

It is necessary to install a C compiler. If you already know how to do this, skip down to [Fixing HTK Source][#fixing-htk-source]. If you are not sure whether you have a C compiler installed, open the Terminal application and type

    gcc -v

If you see `-bash: gcc: command not found`, then you need to install the C compiler. Directions for that follow. ([Skip to directions for OS X Mavericks 10.9][mavericks])

**Lion & Mountain Lion (10.7 & 10.8)**

You need to install command line tools. The here are the steps involved:

1. Go to the [Mac Dev Center](https://developer.apple.com/devcenter/mac/index.action), register (for free) and log in.
2. Go to Downloads, and and then View All Downloads.
3. Search for "command line tools."
4. Download and install the version appropriate for your operating system.

A graphical representation:

*1. Register and login*

![login](readme_img/developer_login.png)

*2. Downloads*

![download1](readme_img/developer_downloads1.png)


*2. View All Downloads*

![download2](readme_img/developer_downloads2.png)

*3 & 4. Search for "command line tools" and download*

![download3](readme_img/developer_downloads3.png)



**Mavericks (10.9)** [mavericks]

`xcode-select --install`

###### Fixing HTK Source


* htk/HTKlib/HRec.c
	* `labid != splabid` -> `labpr != splabid`	

#### sox
#### OS X

## Usage
