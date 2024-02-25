from datetime import datetime
from getpass import getpass
import argparse
import json
import os
import py7zr
import shutil
import subprocess


def main():
    id, secret, password = get_credentials()
    backup_folder = get_backup_name()

    try:
        print("Logging into your vault...")
        bw = Bitwarden(id, secret, password)
        print('                                   done.')

        download_attachments(backup_folder, bw)

        print('Creating json vault export...', end='', flush=True)
        bw.export('export.json', backup_folder)
        print('      done.')

        print('Closing Bitwarden session...', end='', flush=True)
        bw.end_session()
        print('       done.')

        print('Creating encrypted archive...', end='', flush=True)
        zip(backup_folder, password)
        print('      done.')

        print('Deleting temporary files...', end='', flush=True)
        clean_up_files(backup_folder)
        print('        done.')

        print(f'\nALL DONE! Your backup is saved into \'{backup_folder}.7z\'\n')
    except Bitwarden.LoginError as e:
        print(f"Couldn't log you in: {e.message}")
    except Bitwarden.AttachmentError as e:
        print(f"Error during attachment download: {e.message}")
    except Bitwarden.ExportError as e:
        print(f"Error during vault export: {e.message}")


def download_attachments(backup_folder, bw):
    print("Getting all items...", end='', flush=True)
    all_items = bw.get_items()
    print("               done.")
    items_with_attachments = [item for item in all_items if ('attachments' in item)]

    flat_list = [item for sublist in items_with_attachments for item in sublist['attachments']]
    num_attachments = len(flat_list)
    blocks = 40
    blocks_drawn = 0
    print(f'Downloading {num_attachments} attachments...')
    print(f'0%                                  100%')
    downloaded = 0
    for item in items_with_attachments:
        folder = os.path.join(backup_folder, 'attachments', item['name'])
        for attachment in item['attachments']:
            bw.get_attachment(item['id'], attachment, folder)
            downloaded += 1
            while round(downloaded / (num_attachments / blocks)) != blocks_drawn:
                print('█', end='', flush=True)
                blocks_drawn += 1
    print('\n                                   done.')


def get_backup_name():
    now = datetime.now()
    return f"bitwarden-backup-{now.year}-{now.month}-{now.day}_{now.hour}-{now.minute}-{now.second}"


def get_credentials():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', help='Your API client ID')
    parser.add_argument('--secret', help='Your API client secret')
    parser.add_argument('--password', help='Your Bitwarden master password')
    args = parser.parse_args()

    if args.id is not None:
        id = args.id
    else:
        id = getpass(prompt="Please enter your Bitwarden API client ID: ")

    if args.secret is not None:
        secret = args.secret
    else:
        secret = getpass(prompt="Please enter your API client secret: ")

    if args.password is not None:
        password = args.password
    else:
        password = getpass(prompt="Please enter your Bitwarden master password: ")

    return id, secret, password


def zip(folder, password):
    with py7zr.SevenZipFile(
            f'{folder}.7z',
            'w',
            filters=[{'id': py7zr.FILTER_COPY}, {'id': py7zr.FILTER_CRYPTO_AES256_SHA256}],
            password=password
    ) as archive:
        archive.set_encrypted_header(True)
        archive.writeall(folder)


def clean_up_files(temp_folder):
    shutil.rmtree(temp_folder)


class Bitwarden:
    BW_ENV_CLIENTID = "BW_CLIENTID"
    BW_ENV_CLIENTSECRET = "BW_CLIENTSECRET"
    BW_ENV_PASSWORD = "BW_PASSWORD"
    session = None

    def __init__(self, api_client_id, api_client_secret, password):
        os.environ[self.BW_ENV_CLIENTID] = api_client_id
        os.environ[self.BW_ENV_CLIENTSECRET] = api_client_secret
        os.environ[self.BW_ENV_PASSWORD] = password
        try:
            subprocess.check_output([
                'bw', 'login', '--apikey',
                '--nointeraction',
                '--response'
            ])
        except subprocess.CalledProcessError as e:
            message = json.loads(e.output)["message"]
            if message.startswith('You are already logged in as'):
                pass
            else:
                raise Bitwarden.LoginError(message)

        try:
            response = subprocess.check_output([
                'bw', 'unlock',
                '--passwordenv', self.BW_ENV_PASSWORD,
                '--nointeraction',
                '--response'
            ])
            self.session = json.loads(response)['data']['raw']
        except subprocess.CalledProcessError as e:
            raise Bitwarden.LoginError(json.loads(e.output)['message'])

    def export(self, filename, folder='.', format='json'):
        os.makedirs(folder, exist_ok=True)
        try:
            subprocess.check_output([
                'bw', 'export',
                '--output', os.path.join(folder, filename),
                '--format', format,
                '--session', self.session
            ])
        except subprocess.CalledProcessError as e:
            try:
                message = json.loads(e.output)['message']
            except ValueError:
                message = e.output
            raise Bitwarden.ExportError(f'Could not export your vault: {message}')

    def get_items(self):
        try:
            response = subprocess.check_output([
                'bw', 'list', 'items',
                '--nointeraction',
                '--response',
                '--session', self.session
            ])
        except subprocess.CalledProcessError as e:
            raise Bitwarden.AttachmentError(json.loads(e.output)["message"])
        items = json.loads(response)['data']['data']
        return items

    def get_attachment(self, item_id, attachment, folder='.'):
        os.makedirs(folder, exist_ok=True)
        if not folder.endswith('/'):
            folder = f'{folder}/'
        try:
            subprocess.check_output([
                'bw', 'get',
                'attachment', attachment['id'],
                '--itemid', item_id,
                '--output', folder,
                '--session', self.session,
                '--response'
            ])
        except subprocess.CalledProcessError as e:
            try:
                message = json.loads(e.output)['message']
            except ValueError:
                message = e.output
            raise Bitwarden.ExportError(f'Could not download an attachment: {message}')

    def end_session(self):
        subprocess.check_output(['bw', 'lock'])
        subprocess.check_output(['bw', 'logout'])
        os.environ.pop(self.BW_ENV_CLIENTID)
        os.environ.pop(self.BW_ENV_CLIENTSECRET)
        os.environ.pop(self.BW_ENV_PASSWORD)
        self.session = None

    class LoginError(Exception):
        def __init__(self, message):
            self.message = message
            super().__init__(message)

    class AttachmentError(Exception):
        def __init__(self, message):
            self.message = message
            super().__init__(message)

    class ExportError(Exception):
        def __init__(self, message):
            self.message = message
            super().__init__(message)


if __name__ == "__main__":
    main()
