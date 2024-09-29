import json
import os
import pathlib



class Accounts:
    def __init__(self):
        appdata_folder = pathlib.Path(os.environ["APPDATA"])
        self.file_path = os.path.join(appdata_folder, "Mahiro/MineGimmeThat/accounts.json")
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        self.accounts = {}
        self.load()
    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.accounts = json.loads(f.read())
    def account_exists(self, username):
        return username in self.accounts
    def register(self, username, password):
        if username in self.accounts:
            return False
        self.accounts[username] = password
        self.save()
        return True
    def login(self, username, password):
        if username not in self.accounts:
            return False
        return self.accounts[username] == password
    def save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.accounts))
    def delete(self, username, password):
        if username not in self.accounts:
            return False
        if self.accounts[username] != password:
            return False
        self.accounts.pop(username)
        self.save()
        return True
    def change_password(self, username, old_password, new_password):
        if username not in self.accounts:
            return False
        if self.accounts[username] != old_password:
            return False
        self.accounts[username] = new_password
        self.save()
        return True
    @property
    def get_accounts(self):
        return self.accounts