# bitwarden-dl

A small Python script which creates an encrypted Bitwarden backup, including all attachments and supporting YubiKeys.

The script creates a json export of your vault, downloads all attachments and than creates an encrypted 7z archive using your Bitwarden's master password.

## Why?

Bitwarden's own export function is quick and great, but it doesn't download the attachments for you.

For this reason there is a great project called [portwarden](https://github.com/vwxyzjn/portwarden) which offers import and export features. But it only works with e-mail and password combination. This is a problem when you have your account secured using a YubiKey.

Therefor I wrote this script which uses an API client id and key, which is compatible with YubiKey as 2FA. This script only offers export features though for backup reasons.

## Installation

1. Clone this repo or download the files
1. Install Python 
1. Install the requirements
   * `pip install -r requirements.txt`

## Usage

1. Go to [bitwarden.com](https://bitwarden.com) -> Account Settings -> Security -> Keys -> API Key and note your API Key and client id
1. Run the script in the command line
    * `python ./bitwarden-dl.py`
1. Enter the credentials when asked 

### Arguments

Alternatively, instead of entering the credentials manually, you can pass them as arguments. Please see my thoughts about this below.

```commandline
  -h, --help           show this help message and exit
  --id ID              Your API client ID
  --secret SECRET      Your API client secret
  --password PASSWORD  Your Bitwarden master password
```

## Thoughts about security

* All your vault content will be stored in temp files unencrypted during the process. Only use this script on computers you trust and ideally use disc encryption.
* The script stores your credentials in environment variables during its runtime. They could potentially be read out from other programs.
* When passing the credentials as arguments, this should only be done by loading the credentials from a secrets vault, that way they won't land in your command line history.  Something like the Apple Keychain, Powershell SecretManagement or a Linux alternative.