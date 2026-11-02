#!/usr/bin/env python3
"""
 * **************************************************************************
 * Contributions to this work were made on behalf of the GÉANT project,
 * a project that has received funding from the European Union’s Framework
 * Programme 7 under Grant Agreements No. 238875 (GN3)
 * and No. 605243 (GN3plus), Horizon 2020 research and innovation programme
 * under Grant Agreements No. 691567 (GN4-1) and No. 731122 (GN4-2).
 * On behalf of the aforementioned projects, GEANT Association is
 * the sole owner of the copyright in all material which was developed
 * by a member of the GÉANT project.
 * GÉANT Vereniging (Association) is registered with the Chamber of
 * Commerce in Amsterdam with registration number 40535155 and operates
 * in the UK as a branch of GÉANT Vereniging.
 *
 * Registered office: Hoekenrode 3, 1102BR Amsterdam, The Netherlands.
 * UK branch address: City House, 126-130 Hills Road, Cambridge CB2 1PQ, UK
 *
 * License: see the web/copyright.inc.php file in the file structure or
 *          <base_url>/copyright.php after deploying the software

Authors:
    Tomasz Wolniewicz <twoln@umk.pl>
    Michał Gasewicz <genn@umk.pl> (Network Manager support)

Contributors:
    Steffen Klemer https://github.com/sklemer1
    ikreb7 https://github.com/ikreb7
    Dimitri Papadopoulos Orfanos https://github.com/DimitriPapadopoulos
    sdasda7777 https://github.com/sdasda7777
    Matt Jolly http://gitlab.com/Matt.Jolly
    Benoit LE TEXIER benoit.le-texier@imt-atlantique.fr
    jmontes https://github.com/m4r4d0n4

Many thanks for multiple code fixes, feature ideas, styling remarks
much of the code provided by them in the form of pull requests
has been incorporated into the final form of this script.

This script is the main body of the CAT Linux installer.
In the generation process configuration settings are added
as well as messages which are getting translated into the language
selected by the user.

The script runs under python3.

"""
# pylint: disable=broad-except
# pylint: disable=bare-except
# pylint: disable=too-many-lines
# pylint: disable=too-many-branches
# pylint: disable=line-too-long
# pylint: disable=too-few-public-methods
# pylint: disable=fixme

import argparse
import base64
import getpass
import os
import platform
import re
import subprocess
import sys
import uuid
from shutil import copyfile
from typing import List, Optional, Type, Union
from pathlib import Path


NM_AVAILABLE = True
NEW_CRYPTO_AVAILABLE = True
OPENSSL_CRYPTO_AVAILABLE = False
DEBUG_ON = False

parser = argparse.ArgumentParser(description='eduroam linux installer.')
parser.add_argument('--debug', '-d', action='store_true', dest='debug',
    default=False, help='set debug flag')
parser.add_argument('--username', '-u', action='store', dest='username',
    help='set username; the --password and --silent options should be used together with --username')
parser.add_argument('--password', '-p', action='store', dest='password',
    help='set the password; the --username and --silent options should be used together with --password')
parser.add_argument('--silent', '-s', action='store_true', dest='silent',
    help='set silent flag')
parser.add_argument('--pfxfile', action='store', dest='pfx_file',
    help='set path to user certificate file')
parser.add_argument("--wpa_conf", action='store_true', dest='wpa_conf',
    help='generate wpa_supplicant config file without configuring the system')
parser.add_argument("--iwd_conf", action='store_true', dest='iwd_conf',
    help='generate iwd config file without configuring the system')
parser.add_argument("--gui", action='store', dest='gui',
    help='one of: tty, tkinter, zenity, kdialog, yad - use this GUI '
        'system if present, falling back to standard choice if not')
ARGS = parser.parse_args()
if ARGS.debug:
    DEBUG_ON = True
    print("Running debug mode")


def debug(msg) -> None:
    """Print debugging messages to stdout"""
    if not DEBUG_ON:
        return
    print("DEBUG:" + str(msg))


def byte_to_string(barray: List) -> str:
    """conversion utility"""
    return "".join([chr(x) for x in barray])

debug(sys.version_info.major)

try:
    import dbus
except ImportError:
    print("WARNING: Cannot import the dbus module for "+sys.executable+\
        " - please install dbus-python!")
    debug("Cannot import the dbus module for "+sys.executable)
    NM_AVAILABLE = False


try:
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.backends import default_backend
    from cryptography.x509.oid import NameOID
except ImportError:
    NEW_CRYPTO_AVAILABLE = False
    try:
        from OpenSSL import crypto
        crypto.load_pkcs12  # missing in newer versions
        OPENSSL_CRYPTO_AVAILABLE = True
    except (ImportError, AttributeError):  # AttributeError sometimes thrown
                                           # by old/broken OpenSSL versions
        OPENSSL_CRYPTO_AVAILABLE = False


def detect_desktop_environment() -> str:
    """
    Detect what desktop type is used. This method is prepared for
    possible future use with password encryption on supported distros

    the function below was partially copied from
    https://ubuntuforums.org/showthread.php?t=1139057
    """
    desktop_environment = 'generic'
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        desktop_environment = 'kde'
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        desktop_environment = 'gnome'
    else:
        try:
            shell_command = subprocess.Popen(['xprop', '-root',
                                              '_DT_SAVE_MODE'],
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            out, _ = shell_command.communicate()
            info = out.decode('utf-8').strip()
        except (OSError, RuntimeError):
            pass
        else:
            if ' = "xfce4"' in info:
                desktop_environment = 'xfce'
    return desktop_environment


def get_system() -> List:
    """
    Detect Linux platform. Not used at this stage.
    It is meant to enable password encryption in distros
    that can handle this well.
    """
    system = platform.system_alias(
        platform.system(),
        platform.release(),
        platform.version()
    )
    return [system, detect_desktop_environment()]


def get_config_path() -> str:
    """
    Return XDG_CONFIG_HOME path if exists otherwise $HOME/.config
    """

    _config_path = os.environ.get('XDG_CONFIG_HOME')
    if not _config_path:
        _config_path = f'{os.environ.get("HOME")}/.config'

        if not os.path.exists(_config_path):
            os.mkdir(_config_path, 0o755)

    return _config_path


def run_installer() -> None:
    """
    This is the main installer part. It tests for NM availability
    gets user credentials and starts a proper installer.
    """
    username = ''
    password = ''
    silent = False
    pfx_file = ''
    gui = ''
    wpa_conf = False
    iwd_conf = False
    global NM_AVAILABLE

    if ARGS.username:
        username = ARGS.username
    if ARGS.password:
        password = ARGS.password
    if ARGS.silent:
        silent = ARGS.silent
    if ARGS.pfx_file:
        pfx_file = ARGS.pfx_file
    if ARGS.wpa_conf:
        wpa_conf = ARGS.wpa_conf
    if ARGS.iwd_conf:
        iwd_conf = ARGS.iwd_conf
    if ARGS.gui:
        gui = ARGS.gui
    debug(get_system())
    debug("Calling InstallerData")
    installer_data = InstallerData(silent=silent, username=username,
                                   password=password, pfx_file=pfx_file, gui=gui)

    if wpa_conf:
        NM_AVAILABLE = False
    if iwd_conf:
        NM_AVAILABLE = False

    # test dbus connection
    if NM_AVAILABLE:
        config_tool = CatNMConfigTool()
        if config_tool.connect_to_nm() is None:
            NM_AVAILABLE = False
    if not NM_AVAILABLE and not wpa_conf and not iwd_conf:
        # no dbus so ask if the user will want wpa_supplicant config
        if installer_data.ask(Messages.save_wpa_conf, Messages.cont, 1):
            sys.exit(1)
    installer_data.get_user_cred()
    installer_data.save_ca()
    if NM_AVAILABLE:
        config_tool.add_connections(installer_data)
    elif iwd_conf:
        iwd_config = IwdConfiguration()
        for ssid in Config.ssids:
            iwd_config.generate_iwd_config(ssid, installer_data)
    else:
        wpa_config = WpaConf()
        wpa_config.create_wpa_conf(Config.ssids, installer_data)
    installer_data.show_info(Messages.installation_finished)


class Messages:
    """
    These are initial definitions of messages, but they will be
    overridden with translated strings.
    """
    quit = "Really quit?"
    credentials_prompt = "Please, enter your credentials:"
    username_prompt = "enter your userid"
    enter_password = "enter password"
    enter_import_password = "enter your import password"
    incorrect_password = "incorrect password"
    repeat_password = "repeat your password"
    passwords_differ = "passwords do not match"
    empty_field = "one of the fields was empty"
    installation_finished = "Installation successful"
    cat_dir_exists = "Directory {} exists; some of its files may be " \
                     "overwritten."
    cont = "Continue?"
    nm_not_supported = "This NetworkManager version is not supported"
    cert_error = "Certificate file not found, looks like a CAT error"
    unknown_version = "Unknown version"
    dbus_error = "DBus connection problem, a sudo might help"
    ok = "OK"
    yes = "Y"
    no = "N"
    p12_filter = "personal certificate file (p12 or pfx)"
    all_filter = "All files"
    p12_title = "personal certificate file (p12 or pfx)"
    save_wpa_conf = "NetworkManager configuration failed. " \
                    "Ensure you have the dbus-python package for your distro installed on your system. " \
                    "We may generate a wpa_supplicant configuration file " \
                    "if you wish. Be warned that your connection password will be saved " \
                    "in this file as clear text."
    save_wpa_confirm = "Write the file"
    wrong_username_format = "Error: Your username must be of the form " \
                          "'xxx@institutionID' e.g. 'john@example.net'!"
    wrong_realm = "Error: your username must be in the form of 'xxx@{}'. " \
                  "Please enter the username in the correct format."
    wrong_realm_suffix = "Error: your username must be in the form of " \
                         "'xxx@institutionID' and end with '{}'. Please enter the username " \
                         "in the correct format."
    user_cert_missing = "personal certificate file not found"
    # "File %s exists; it will be overwritten."
    # "Output written to %s"


class Config:
    """
    This is used to prepare settings during installer generation.
    """
    instname = ""
    profilename = ""
    url = ""
    email = ""
    title = "eduroam CAT"
    servers = []
    ssids = []
    del_ssids = []
    eap_outer = ''
    eap_inner = ''
    use_other_tls_id = False
    server_match = ''
    anonymous_identity = ''
    CA = ""
    init_info = ""
    init_confirmation = ""
    tou = ""
    sb_user_file = ""
    verify_user_realm_input = False
    user_realm = ""
    hint_user_input = False


class InstallerData:
    """
    General user interaction handling, supports zenity, KDialog, yad and
    standard command-line interface
    """

    def __init__(self, silent: bool = False, username: str = '',
                 password: str = '', pfx_file: str = '', gui: str = '') -> None:
        self.graphics = ''
        self.username = username
        self.password = password
        self.silent = silent
        self.pfx_file = pfx_file
        self.install_wired = False
        self.rehash = False
        if gui in ('tty', 'tkinter', 'yad', 'zenity', 'kdialog'):
            self.gui = gui
        else:
            self.gui = ''
        debug("starting constructor")
        if silent:
            self.graphics = 'tty'
        else:
            self.__get_graphics_support()
        self.show_info(Config.init_info.format(Config.instname,
                                               Config.email, Config.url))
        if self.ask(Config.init_confirmation.format(Config.instname,
                                                    Config.profilename),
                    Messages.cont, 1):
            sys.exit(1)
        if Config.tou != '':
            if self.ask(Config.tou, Messages.cont, 1):
                sys.exit(1)
        if NM_AVAILABLE is True and self.__has_active_wired_interface() and Config.wired != '':
            if self.ask(Messages.wired):
                debug("Wired will be omittted")
            else:
                self.install_wired = True
                debug("Wired will be set")
        if os.path.exists(get_config_path() + '/cat_installer'):
            if self.ask(Messages.cat_dir_exists.format(
                    get_config_path() + '/cat_installer'),
                    Messages.cont, 1):
                sys.exit(1)
        else:
            os.mkdir(get_config_path() + '/cat_installer', 0o700)
            os.mkdir(get_config_path() + '/cat_installer/ca', 0o700)


    def save_ca(self) -> None:
        """
        Save CA certificate to cat_installer directory
        (create directory if needed)
        We use separate per certificate files in the ca directory only
        in the special case handling the NM bug for versions between 1.54.3 and
        1.58.0. This is controlled by the self.rehash setting which was done
        during the NM version testing.
        """
        if self.rehash:
            ca_dir = get_config_path() + '/cat_installer/ca'
            os.makedirs(ca_dir, 0o700, exist_ok=True)
            for old in os.listdir(ca_dir):
                os.remove(os.path.join(ca_dir, old))
            # one file per certificate under cat_installer/ca/
            pattern = r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----'
            certs = re.findall(pattern, Config.CA, re.DOTALL)
            for index, cert_pem in enumerate(certs):
                with open(os.path.join(ca_dir, f'ca-{index}.pem'), 'w') as f:
                    f.write(cert_pem + "\n")
            if (index > 0):
                try:
                    subprocess.run(['openssl', 'rehash', ca_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                except (OSError, RuntimeError):
                    pass
            if not any(entry.is_symlink() for entry in Path(ca_dir).iterdir()):
                self.rehash = False
        if not self.rehash:
            certfile = get_config_path() + '/cat_installer/ca.pem'
            debug("saving cert")
            with open(certfile, 'w') as cert:
                cert.write(Config.CA + "\n")


    def ask(self, question: str, prompt: str = '', default: Optional[bool] = None) -> int:
        """
        Prompt user for a Y/N reply, possibly supplying a default answer
        """
        if self.silent:
            return 0
        if self.graphics == 'tty':
            yes = Messages.yes[:1].upper()
            nay = Messages.no[:1].upper()
            print("\n-------\n" + question + "\n")
            while True:
                tmp = prompt + " (" + Messages.yes + "/" + Messages.no + ") "
                if default == 1:
                    tmp += "[" + yes + "]"
                elif default == 0:
                    tmp += "[" + nay + "]"
                inp = input(tmp)
                if inp == '':
                    if default == 1:
                        return 0
                    if default == 0:
                        return 1
                i = inp[:1].upper()
                if i == yes:
                    return 0
                if i == nay:
                    return 1
        elif self.graphics == 'tkinter':
            from tkinter import messagebox
            return 0 if messagebox.askyesno(Config.title, question + "\n\n" + prompt) else 1
        else:
            command = []
            if self.graphics == 'zenity':
                command = ['zenity', '--title=' + Config.title, '--width=500',
                           '--question', '--text=' + question + "\n\n" + prompt]
            elif self.graphics == 'kdialog':
                command = ['kdialog', '--yesno', question + "\n\n" + prompt,
                           '--title=' + Config.title]
            elif self.graphics == 'yad':
                command = ['yad', '--image="dialog-question"',
                           '--button=yad-yes:0',
                           '--button=yad-no:1',
                           '--width=500',
                           '--wrap',
                           '--text=' + question + "\n\n" + prompt,
                           '--title=' + Config.title]
            return subprocess.call(command, stderr=subprocess.DEVNULL)


    def show_info(self, data: str) -> None:
        """
        Show a piece of information
        """
        if self.silent:
            return
        if self.graphics == 'tty':
            print(data)
        elif self.graphics == 'tkinter':
            from tkinter import messagebox
            messagebox.showinfo(Config.title, data)
        else:
            if self.graphics == 'zenity':
                command = ['zenity', '--info', '--width=500', '--text=' + data]
            elif self.graphics == 'kdialog':
                command = ['kdialog', '--msgbox', data, '--title=' + Config.title]
            elif self.graphics == "yad":
                command = ['yad', '--button=OK', '--width=500', '--text=' + data]
            else:
                sys.exit(1)
            subprocess.call(command, stderr=subprocess.DEVNULL)


    def confirm_exit(self) -> None:
        """
        Confirm exit from installer
        """
        ret = self.ask(Messages.quit)
        if ret == 0:
            sys.exit(1)


    def alert(self, text: str) -> None:
        """Generate alert message"""
        if self.silent:
            return
        if self.graphics == 'tty':
            print(text)
        elif self.graphics == 'tkinter':
            from tkinter import messagebox
            messagebox.showwarning(Config.title, text)
        else:
            if self.graphics == 'zenity':
                command = ['zenity', '--warning', '--text=' + text]
            elif self.graphics == "kdialog":
                command = ['kdialog', '--sorry', text, '--title=' + Config.title]
            elif self.graphics == "yad":
                command = ['yad', '--text=' + text]
            else:
                sys.exit(1)
            subprocess.call(command, stderr=subprocess.DEVNULL)


    def prompt_nonempty_string(self, show: int, prompt: str, val: str = '') -> str:
        """
        Prompt user for input
        """
        if self.graphics == 'tty':
            if show == 0:
                while True:
                    inp = str(getpass.getpass(prompt + ": "))
                    output = inp.strip()
                    if output != '':
                        return output
            while True:
                inp = input(prompt + ": ")
                output = inp.strip()
                if output != '':
                    return output
        elif self.graphics == 'tkinter':
            from tkinter import simpledialog
            while True:
                output = simpledialog.askstring(Config.title, prompt,
                                                initialvalue=val,
                                                show="*" if show == 0 else "")
                if output:
                    return output

        else:
            command = []
            if self.graphics == 'zenity':
                if val == '':
                    default_val = ''
                else:
                    default_val = '--entry-text=' + val
                if show == 0:
                    hide_text = '--hide-text'
                else:
                    hide_text = ''
                command = ['zenity', '--entry', hide_text, default_val,
                           '--width=500', '--text=' + prompt]
            elif self.graphics == 'kdialog':
                if show == 0:
                    hide_text = '--password'
                else:
                    hide_text = '--inputbox'
                command = ['kdialog', hide_text, prompt, '--title=' + Config.title]
            elif self.graphics == 'yad':
                if show == 0:
                    hide_text = ':H'
                else:
                    hide_text = ''
                command = ['yad', '--form', '--field=' + hide_text,
                           '--text=' + prompt, val]

            output = ''
            while not output:
                shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                out, _ = shell_command.communicate()
                output = out.decode('utf-8')
                if self.graphics == 'yad':
                    output = output[:-2]
                output = output.strip()
                if shell_command.returncode == 1:
                    self.confirm_exit()
            return output


    def __get_username_password_atomic(self) -> None:
        """
        use single form to get username, password and password confirmation
        """
        output_fields_separator = "\n\n\n\n\n"
        while True:
            password = "a"
            password1 = "b"
            if self.graphics == 'tkinter':
                import tkinter as tk

                root = tk.Tk()
                root.title(Config.title)

                desc_label = tk.Label(root, text=Messages.credentials_prompt)
                desc_label.grid(row=0, column=0, columnspan=2, sticky=tk.W)

                username_label = tk.Label(root, text=Messages.username_prompt)
                username_label.grid(row=1, column=0, sticky=tk.W)

                username_entry = tk.Entry(root, textvariable=tk.StringVar(root, value=self.username))
                username_entry.grid(row=1, column=1)

                password_label = tk.Label(root, text=Messages.enter_password)
                password_label.grid(row=2, column=0, sticky=tk.W)

                password_entry = tk.Entry(root, show="*")
                password_entry.grid(row=2, column=1)

                password1_label = tk.Label(root, text=Messages.repeat_password)
                password1_label.grid(row=3, column=0, sticky=tk.W)

                password1_entry = tk.Entry(root, show="*")
                password1_entry.grid(row=3, column=1)

                def submit(installer):
                    def inner():
                        nonlocal password, password1
                        (installer.username, password, password1) = (username_entry.get(), password_entry.get(), password1_entry.get())
                        root.destroy()
                    return inner

                login_button = tk.Button(root, text=Messages.ok, command=submit(self))
                login_button.grid(row=4, column=0, columnspan=2)

                root.mainloop()
            else:
                if self.graphics == 'zenity':
                    command = ['zenity', '--forms', '--width=500',
                               f"--title={Config.title}",
                               f"--text={Messages.credentials_prompt}",
                               f"--add-entry={Messages.username_prompt}",
                               f"--add-password={Messages.enter_password}",
                               f"--add-password={Messages.repeat_password}",
                               "--separator", output_fields_separator]
                elif self.graphics == 'yad':
                    command = ['yad', '--form',
                               f"--title={Config.title}",
                               f"--text={Messages.credentials_prompt}",
                               f"--field={Messages.username_prompt}", self.username,
                               f"--field={Messages.enter_password}:H",
                               f"--field={Messages.repeat_password}:H",
                               "--separator", output_fields_separator]

                output = ''
                while not output:
                    shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                                     stderr=subprocess.PIPE)
                    out, _ = shell_command.communicate()
                    output = out.decode('utf-8')
                    if self.graphics == 'yad':
                        output = output[:-(len(output_fields_separator)+1)]
                    output = output.strip()
                    if shell_command.returncode == 1:
                        self.confirm_exit()

                if self.graphics in ('zenity', 'yad'):
                    fields = output.split(output_fields_separator)
                    if len(fields) != 3:
                        self.alert(Messages.empty_field)
                        continue
                    self.username, password, password1 = fields

            if not self.__validate_user_name():
                continue
            if password != password1:
                self.alert(Messages.passwords_differ)
                continue
            self.password = password
            break


    def get_user_cred(self) -> None:
        """
        Get user credentials both username/password and personal certificate
        based
        """
        if Config.eap_outer in ('PEAP', 'TTLS'):
            self.__get_username_password()
        elif Config.eap_outer == 'TLS':
            self.__get_p12_cred()


    def __get_username_password(self) -> None:
        """
        read user password and set the password property
        do nothing if silent mode is set
        """
        if self.silent:
            return
        if self.graphics in ('tkinter', 'zenity', 'yad'):
            self.__get_username_password_atomic()
        else:
            password = "a"
            password1 = "b"
            if self.username:
                user_prompt = self.username
            elif Config.hint_user_input:
                user_prompt = '@' + Config.user_realm
            else:
                user_prompt = ''
            while True:
                self.username = self.prompt_nonempty_string(
                    1, Messages.username_prompt, user_prompt)
                if self.__validate_user_name():
                    break
            while password != password1:
                password = self.prompt_nonempty_string(
                    0, Messages.enter_password)
                password1 = self.prompt_nonempty_string(
                    0, Messages.repeat_password)
                if password != password1:
                    self.alert(Messages.passwords_differ)
            self.password = password

    def __check_graphics(self, command) -> bool:
        shell_command = subprocess.Popen(['which', command],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        shell_command.wait()
        if shell_command.returncode == 0:
            self.graphics = command
            debug("Using "+command)
            return True
        return False


    def __get_graphics_support(self) -> None:
        self.graphics = 'tty'
        if self.gui == 'tty':
            return
        if os.environ.get('DISPLAY') is None:
            return
        if self.gui and self.gui != 'tkinter':
            if self.__check_graphics(self.gui):
                return
            try:
                import tkinter  # noqa: F401
            except Exception:
                pass
            else:
                self.graphics = 'tkinter'
                return
        for cmd in ('yad', 'zenity', 'kdialog'):
            if self.__check_graphics(cmd):
                return


    def __process_p12(self) -> bool:
        debug('process_p12')
        pfx_file = get_config_path() + '/cat_installer/user.p12'
        if NEW_CRYPTO_AVAILABLE:
            debug("using new crypto")
            try:
                p12 = pkcs12.load_key_and_certificates(
                                        open(pfx_file,'rb').read(),
                                        self.password, backend=default_backend())
            except Exception as error:
                debug(f"Incorrect password ({error}).")
                return False
            else:
                if Config.use_other_tls_id:
                    return True
                try:
                    self.username = p12[1].subject.\
                        get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
                except Exception:
                    self.username = p12[1].subject.\
                        get_attributes_for_oid(NameOID.EMAIL_ADDRESS)[0].value
                return True
        if OPENSSL_CRYPTO_AVAILABLE:
            debug("using openssl crypto")
            try:
                p12 = crypto.load_pkcs12(open(pfx_file, 'rb').read(),
                                         self.password)
            except crypto.Error as error:
                debug(f"Incorrect password ({error}).")
                return False
            else:
                if Config.use_other_tls_id:
                    return True
                try:
                    self.username = p12.get_certificate(). \
                        get_subject().commonName
                except crypto.Error:
                    self.username = p12.get_certificate().\
                        get_subject().emailAddress
                return True
        debug("using openssl")
        command = ['openssl', 'pkcs12', '-in', pfx_file, '-passin',
                   'pass:' + self.password, '-nokeys', '-clcerts']
        shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        out, _ = shell_command.communicate()
        if shell_command.returncode != 0:
            debug("first password run failed")
            command1 = ['openssl', 'pkcs12', '-legacy', '-in', pfx_file, '-passin',
                        'pass:' + self.password, '-nokeys', '-clcerts']
            shell_command1 = subprocess.Popen(command1, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE)
            out, _err = shell_command1.communicate()
            if shell_command1.returncode != 0:
                return False
        if Config.use_other_tls_id:
            return True
        out_str = out.decode('utf-8').strip()
        # split only on commas that are not inside double quotes
        subject = re.split(r'\s*[/,]\s*(?=([^"]*"[^"]*")*[^"]*$)',
                           re.findall(r'subject=/?(.*)$',
                                      out_str, re.MULTILINE)[0])
        cert_prop = {}
        for field in subject:
            if field:
                cert_field = re.split(r'\s*=\s*', field)
                cert_prop[cert_field[0].lower()] = cert_field[1]
        if cert_prop['cn'] and re.search(r'@', cert_prop['cn']):
            debug('Using cn: ' + cert_prop['cn'])
            self.username = cert_prop['cn']
        elif cert_prop['emailaddress'] and \
                re.search(r'@', cert_prop['emailaddress']):
            debug('Using email: ' + cert_prop['emailaddress'])
            self.username = cert_prop['emailaddress']
        else:
            self.username = ''
            self.alert("Unable to extract username "
                       "from the certificate")
        return True


    def __select_p12_file(self) -> str:
        """
        prompt user for the PFX file selection
        this method is not being called in the silent mode
        therefore there is no code for this case
        """
        if self.graphics == 'tty':
            my_dir = os.listdir(".")
            p_count = 0
            pfx_file = ''
            for my_file in my_dir:
                if my_file.endswith(('.p12', '.pfx', '.P12', '.PFX')):
                    p_count += 1
                    pfx_file = my_file
            prompt = "personal certificate file (p12 or pfx)"
            default = ''
            if p_count == 1:
                default = '[' + pfx_file + ']'

            while True:
                inp = input(prompt + default + ": ")
                output = inp.strip()

                if default != '' and output == '':
                    return pfx_file
                default = ''
                if os.path.isfile(output):
                    return output
                print("file not found")

        cert = ""
        if self.graphics == 'zenity':
            command = ['zenity', '--file-selection',
                       '--file-filter=' + Messages.p12_filter +
                       ' | *.p12 *.P12 *.pfx *.PFX', '--file-filter=' +
                       Messages.all_filter + ' | *',
                       '--title=' + Messages.p12_title]
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            cert, _ = shell_command.communicate()
        if self.graphics == 'kdialog':
            command = ['kdialog', '--getopenfilename', '.',
                       '--title=' + Messages.p12_title]
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=subprocess.DEVNULL)
            cert, _ = shell_command.communicate()
        if self.graphics == 'yad':
            command = ['yad', '--file',
                       '--file-filter=*.p12 *.P12 *.pfx *.PFX',
                       '-file-filter=*', '--title=' + Messages.p12_title]
            shell_command = subprocess.Popen(command, stdout=subprocess.PIPE,
                                             stderr=subprocess.DEVNULL)
            cert, _ = shell_command.communicate()
        if self.graphics == 'tkinter':
            from tkinter import filedialog as fd
            return fd.askopenfilename(title=Messages.p12_title,
                                      filetypes=(("Certificate file",
                                                  ("*.p12", "*.P12", "*.pfx",
                                                   "*.PFX")),))
        return cert.decode('utf-8').strip()

    @staticmethod
    def __save_sb_pfx() -> None:
        """write the user PFX file"""
        cert_file = get_config_path() + '/cat_installer/user.p12'
        with open(cert_file, 'wb') as cert:
            cert.write(base64.b64decode(Config.sb_user_file))


    def __get_p12_cred(self):
        """get the password for the PFX file"""
        if Config.eap_inner == 'SILVERBULLET':
            self.__save_sb_pfx()
        else:
            if not self.silent:
                self.pfx_file = self.__select_p12_file()
            try:
                copyfile(self.pfx_file, get_config_path() +
                         '/cat_installer/user.p12')
            except (OSError, RuntimeError):
                print(Messages.user_cert_missing)
                sys.exit(1)
        if self.silent:
            username = self.username
            if not self.__process_p12():
                sys.exit(1)
            if username:
                self.username = username
        else:
            while not self.password:
                self.password = self.prompt_nonempty_string(
                    0, Messages.enter_import_password).encode('utf-8')
                if not self.__process_p12():
                    self.alert(Messages.incorrect_password)
                    self.password = ''
            if not self.username:
                self.username = self.prompt_nonempty_string(
                    1, Messages.username_prompt)


    def __validate_user_name(self) -> bool:
        # locate the @ character in username
        pos = self.username.find('@')
        debug("@ position: " + str(pos))
        # trailing @
        if pos == len(self.username) - 1:
            debug("username ending with @")
            self.alert(Messages.wrong_username_format)
            return False
        # no @ at all
        if pos == -1:
            if Config.verify_user_realm_input:
                debug("missing realm")
                self.alert(Messages.wrong_username_format)
                return False
            debug("No realm, but possibly correct")
            return True
        # @ at the beginning
        if pos == 0:
            debug("missing user part")
            self.alert(Messages.wrong_username_format)
            return False
        pos += 1
        if Config.verify_user_realm_input:
            if Config.hint_user_input:
                if self.username.endswith('@' + Config.user_realm, pos - 1):
                    debug("realm equal to the expected value")
                    return True
                debug("incorrect realm; expected:" + Config.user_realm)
                self.alert(Messages.wrong_realm.format(Config.user_realm))
                return False
            if self.username.endswith(Config.user_realm, pos):
                debug("realm ends with expected suffix")
                return True
            debug("realm suffix error; expected: " + Config.user_realm)
            self.alert(Messages.wrong_realm_suffix.format(
                Config.user_realm))
            return False
        pos1 = self.username.find('@', pos)
        if pos1 > -1:
            debug("second @ character found")
            self.alert(Messages.wrong_username_format)
            return False
        pos1 = self.username.find('.', pos)
        if pos1 == pos:
            debug("a dot immediately after the @ character")
            self.alert(Messages.wrong_username_format)
            return False
        debug("all passed")
        return True


    def __has_active_wired_interface(self):
        result = subprocess.run(
            ['ip', '-o', 'link', 'show'],
            capture_output=True, text=True
        )
        for line in result.stdout.splitlines():
            if re.search(r'\b(lo|wl\w+|docker\d+|virbr\d+|tun\d+|br-\w+|veth\w+)\b', line):
                continue
            if re.search(r'\b(eth|en[opsx]|eno|enp|ens)\d', line, re.IGNORECASE):
                return True
        return False


class WpaConf:
    """
    Prepare and save wpa_supplicant config file
    """

    @staticmethod
    def __prepare_network_block(ssid: str, user_data: Type[InstallerData]) -> str:
        interface = """network={
        ssid=\"""" + ssid + """\"
        key_mgmt=WPA-EAP
        pairwise=CCMP
        group=CCMP
        eap=""" + Config.eap_outer + """
        ca_cert=\"""" + get_config_path() + """/cat_installer/ca.pem\"""""""
        identity=\"""" + user_data.username + """\"""""""
        altsubject_match=\"""" + ";".join(Config.servers) + """\"
        """

        if Config.eap_outer in ('PEAP', 'TTLS'):
            if Config.anonymous_identity != '':
                outer_identity = Config.anonymous_identity
            else:
                outer_identity = user_data.username
            interface += f"phase2=\"auth={Config.eap_inner}\"\n" \
                         f"\tpassword=\"{user_data.password}\"\n" \
                         f"\tanonymous_identity=\"{outer_identity}\"\n"
        elif Config.eap_outer == 'TLS':
            interface += "\tprivate_key_passwd=\"{}\"\n" \
                         "\tprivate_key=\"{}/.cat_installer/user.p12" \
                         .format(user_data.password, os.environ.get('HOME'))
        interface += "\n}"
        return interface


    def create_wpa_conf(self, ssids, user_data: Type[InstallerData]) -> None:
        """Create and save the wpa_supplicant config file"""
        wpa_conf = get_config_path() + '/cat_installer/cat_installer.conf'
        with open(wpa_conf, 'w') as conf:
            for ssid in ssids:
                net = self.__prepare_network_block(ssid, user_data)
                conf.write(net)

class IwdConfiguration:
    """ support the iNet wireless daemon by Intel """

    def __init__(self):
        self.config = ""


    def write_config(self, ssid: str) -> None:
        """
        Write out an iWD config for a given SSID;
        if permissions are insufficient (e.g. wayland),
        use pkexec to elevate a shell and echo the config into the file.
        """

        file_path = f'{ssid}.8021x'
        try:
            with open(file_path, 'w') as config_file:
                debug("writing: "+file_path)
                config_file.write(self.config)
        except PermissionError:
            command = f'echo "{self.config}" > {file_path}'
            subprocess.run(['pkexec', 'bash', '-c', command], check=True)


    def generate_iwd_config(self, ssid: str, user_data: Type[InstallerData]) -> None:
        """Generate an appropriate IWD 8021x config for a given EAP method"""
        #TODO: It would probably be best to generate these configs from scratch but the logic is a little harder
        #      This would add flexibility when dealing with inner and outer config types.
        if Config.eap_outer == 'PWD':
            self._create_eap_pwd_config(user_data)
        elif Config.eap_outer == 'PEAP':
            self._create_eap_peap_config(user_data)
        elif Config.eap_outer == 'TTLS':
            self._create_ttls_pap_config(user_data)
        else:
            msg = 'Invalid_connection_type'
            raise ValueError(msg)
        self.write_config(ssid)


    def _create_eap_pwd_config(self, user_data: Type[InstallerData]) -> None:
        """ create EAP-PWD configuration """
        self.config = f"""
[Security]
EAP-Method=PWD
EAP-Identity={user_data.username}
EAP-Password={user_data.password}

[Settings]
AutoConnect=true
"""

    def _create_eap_peap_config(self, user_data: Type[InstallerData]) -> None:
        """ create EAP-PEAP configuration """
        if Config.anonymous_identity != '':
            outer_identity = Config.anonymous_identity
        else:
            outer_identity = user_data.username
        self.config = f"""
[Security]
EAP-Method=PEAP
EAP-Identity={outer_identity}
EAP-PEAP-CACert=embed:eduroam_ca_cert
EAP-PEAP-ServerDomainMask={Config.servers_cn}
EAP-PEAP-Phase2-Method=MSCHAPV2
EAP-PEAP-Phase2-Identity={user_data.username}
EAP-PEAP-Phase2-Password={user_data.password}

[Settings]
AutoConnect=true

[@pem@eduroam_ca_cert]
{Config.CA}
"""

    def _create_ttls_pap_config(self, user_data: Type[InstallerData]) -> None:
        """ create TTLS-PAP configuration"""
        if Config.anonymous_identity != '':
            outer_identity = Config.anonymous_identity
        else:
            outer_identity = user_data.username
        self.config = f"""
[Security]
EAP-Method=TTLS
EAP-Identity={outer_identity}
EAP-TTLS-CACert=embed:eduroam_ca_cert
EAP-TTLS-ServerDomainMask={Config.servers_cn}
EAP-TTLS-Phase2-Method=Tunneled-PAP
EAP-TTLS-Phase2-Identity={user_data.username}
EAP-TTLS-Phase2-Password={user_data.password}

[Settings]
AutoConnect=true

[@pem@eduroam_ca_cert]
{Config.CA}
"""

class CatNMConfigTool:
    """
    Prepare and save NetworkManager configuration
    """

    def __init__(self):
        self.cacert_location = None
        self.settings_service_name = None
        self.connection_interface_name = None
        self.system_service_name = "org.freedesktop.NetworkManager"
        self.nm_version = None
        self.pfx_file = None
        self.settings = None
        self.user_data = None
        self.bus = None


    def connect_to_nm(self) -> Union[bool, None]:
        """
        connect to DBus
        """
        try:
            self.bus = dbus.SystemBus()
        except AttributeError:
            # since dbus existed but is empty we have an empty package
            # this gets shipped by pyqt5
            print("DBus not properly installed")
            return None
        except dbus.exceptions.DBusException:
            print("Can't connect to DBus")
            return None
        # check NM version
        self.__check_nm_version()
        debug("Actual NM version: " + self.nm_version_real)
        debug("NM version used: " + self.nm_version)
        if self.nm_version_float >= 0.9:
            self.settings_service_name = self.system_service_name
            self.connection_interface_name = \
                "org.freedesktop.NetworkManager.Settings.Connection"
            # settings proxy
            sysproxy = self.bus.get_object(
                self.settings_service_name,
                "/org/freedesktop/NetworkManager/Settings")
            # settings interface
            self.settings = dbus.Interface(sysproxy, "org.freedesktop."
                                                     "NetworkManager.Settings")
        elif self.nm_version == "0.8":
            self.settings_service_name = "org.freedesktop.NetworkManager"
            self.connection_interface_name = "org.freedesktop.NetworkMana" \
                                             "gerSettings.Connection"
            # settings proxy
            sysproxy = self.bus.get_object(
                self.settings_service_name,
                "/org/freedesktop/NetworkManagerSettings")
            # settings interface
            self.settings = dbus.Interface(
                sysproxy, "org.freedesktop.NetworkManagerSettings")
        else:
            print(Messages.nm_not_supported)
            return None
        debug("NM connection worked")
        return True


    def __check_opts(self) -> None:
        """
        set certificate files paths and test for existence of the CA cert
        """
        if self.user_data.rehash:
            self.cacert_location = get_config_path() + '/cat_installer/ca'
            has_cert = any(Path(self.cacert_location).glob('*.pem'))
        else:
            self.cacert_location = get_config_path() + '/cat_installer/ca.pem'
            has_cert = os.path.isfile(self.cacert_location)
        self.pfx_file = get_config_path() + '/cat_installer/user.p12'
        if not has_cert:
            print(Messages.cert_error)
            sys.exit(2)


    def __check_nm_version(self) -> None:
        """
        Get the NetworkManager version
        """
        self.nm_version_float = 0.0
        self.nm_version = Messages.unknown_version
        self.nm_version_real = Messages.unknown_version
        try:
            proxy = self.bus.get_object(
                self.system_service_name, "/org/freedesktop/NetworkManager")
            props = dbus.Interface(proxy, "org.freedesktop.DBus.Properties")
            self.nm_version_real = props.Get("org.freedesktop.NetworkManager", "Version")
            m = re.search(r"(\d\.\d*).(\d*)", self.nm_version_real)
            self.nm_version_float = float(m.group(1))
            subver = int(m.group(2))
        except dbus.exceptions.DBusException:
            version = ""

        if self.nm_version_float >= 1.58 and subver >= 1:
            self.nm_version = "1.58.1"
            return
        if self.nm_version_float >= 1.54 and subver >= 3:
            self.nm_version = "1.54.3"
            self.rehash = True
            return
        if self.nm_version_float >= 1.24:
            self.nm_version = "1.24"
            return
        if re.match(r'^1\.', version):
            self.nm_version = "1.0"
            return
        if re.match(r'^0\.9', version):
            self.nm_version = "0.9"
            return
        if re.match(r'^0\.8', version):
            self.nm_version = "0.8"
            return




    def __delete_existing_connection(self, ssid: str) -> None:
        """
        checks and deletes earlier connection
        """
        try:
            conns = self.settings.ListConnections()
        except dbus.exceptions.DBusException:
            print(Messages.dbus_error)
            sys.exit(3)
        for each in conns:
            con_proxy = self.bus.get_object(self.system_service_name, each)
            connection = dbus.Interface(
                con_proxy,
                "org.freedesktop.NetworkManager.Settings.Connection")
            try:
                connection_settings = connection.GetSettings()
                if connection_settings['connection']['type'] == '802-11-' \
                                                                'wireless':
                    conn_ssid = byte_to_string(
                        connection_settings['802-11-wireless']['ssid'])
                    if conn_ssid == ssid:
                        debug("deleting connection: " + conn_ssid)
                        connection.Delete()
            except dbus.exceptions.DBusException:
                pass


    def __delete_existing_wired_connections(self) -> None:
        """
        checks and deletes earlier connection
        """
        try:
            conns = self.settings.ListConnections()
        except dbus.exceptions.DBusException:
            print(Messages.dbus_error)
            sys.exit(3)
        for each in conns:
            con_proxy = self.bus.get_object(self.system_service_name, each)
            connection = dbus.Interface(
                con_proxy,
                "org.freedesktop.NetworkManager.Settings.Connection")
            try:
                connection_settings = connection.GetSettings()
                conn_id = connection_settings['connection']['id']
                if connection_settings['connection']['type'] == '802-3-ethernet' and \
                    (conn_id in ('wired-eduroam')):
                    debug("Deleting wired connection " + conn_id)
                    connection.Delete()
            except dbus.exceptions.DBusException:
                pass


    def __prepare_connection_data(self):
        server_alt_subject_name_list = dbus.Array(Config.servers)
        server_cn_list = Config.servers_cn
        server_name = Config.server_match
        if self.nm_version_float >= 1.24:
            match_key = 'domain-match'
            match_value = server_cn_list
        elif self.nm_version in ("0.9", "1.0"):
            match_key = 'altsubject-matches'
            match_value = server_alt_subject_name_list
        else:
            match_key = 'subject-match'
            match_value = server_name

        if self.user_data.rehash:
            ca_spec_key = 'ca-path'
            ca_spec_value = self.cacert_location
        else:
            ca_spec_key = 'ca-cert'
            ca_spec_value = dbus.ByteArray(f"file://{self.cacert_location}\0".encode())
        if Config.anonymous_identity != '':
            outer_identity = Config.anonymous_identity
        else:
            outer_identity = self.user_data.username
        s_8021x_data = {
            'eap': [Config.eap_outer.lower()],
            'identity': self.user_data.username,
            ca_spec_key: ca_spec_value,
            match_key: match_value}
        if Config.eap_outer in ('PEAP', 'TTLS'):
            s_8021x_data['password'] = self.user_data.password
            s_8021x_data['phase2-auth'] = Config.eap_inner.lower()
            if Config.anonymous_identity != '':
                s_8021x_data['anonymous-identity'] = outer_identity
            s_8021x_data['password-flags'] = 1
        elif Config.eap_outer == 'TLS':
            s_8021x_data['client-cert'] = dbus.ByteArray(
                f"file://{self.pfx_file}\0".encode())
            s_8021x_data['private-key'] = dbus.ByteArray(
                f"file://{self.pfx_file}\0".encode())
            s_8021x_data['private-key-password'] = self.user_data.password
            s_8021x_data['private-key-password-flags'] = 1
        return dbus.Dictionary(s_8021x_data)


    def __add_wired_connection(self, s_8021x):
        s_ip4 = dbus.Dictionary({'method': 'auto'})
        s_ip6 = dbus.Dictionary({'method': 'auto'})
        s_con_eduroam = dbus.Dictionary({
            'type': '802-3-ethernet',
            'autoconnect-priority': 100,
            'autoconnect-retries' : 3,
            'uuid': str(uuid.uuid4()),
            'permissions': ['user:' + os.environ.get('USER')],
            'id': 'wired-eduroam'
        })

        s_8021x['optional'] = True
        s_8021x['auth-timeout'] = 10
        con = dbus.Dictionary({
            'connection': s_con_eduroam,
            '802-1x': s_8021x,
            'ipv4': s_ip4,
            'ipv6': s_ip6
        })
        debug("ADDING wired-eduroam")
        self.settings.AddConnection(con)


    def __add_wifi_connection(self, s_8021x, ssid):
        s_ip4 = dbus.Dictionary({'method': 'auto'})
        s_ip6 = dbus.Dictionary({'method': 'auto'})
        s_con = dbus.Dictionary({
            'type': '802-11-wireless',
            'uuid': str(uuid.uuid4()),
            'permissions': ['user:' + os.environ.get('USER')],
            'id': ssid
        })
        s_wifi = dbus.Dictionary({
            'ssid': dbus.ByteArray(ssid.encode('utf8')),
            'security': '802-11-wireless-security'
        })
        s_wsec = dbus.Dictionary({
            'key-mgmt': 'wpa-eap',
            'proto': ['rsn'],
            'pairwise': ['ccmp'],
            'group': ['ccmp']
        })

        con = dbus.Dictionary({
            'connection': s_con,
            '802-11-wireless': s_wifi,
            '802-11-wireless-security': s_wsec,
            '802-1x': s_8021x,
            'ipv4': s_ip4,
            'ipv6': s_ip6
        })
        self.settings.AddConnection(con)


    def add_connections(self, user_data: Type[InstallerData]):
        """Delete and then add connections to the system"""
        self.user_data = user_data
        self.__check_opts()
        s_8021x = self.__prepare_connection_data()
        for ssid in Config.ssids:
            self.__delete_existing_connection(ssid)
            self.__add_wifi_connection(s_8021x, ssid)
        for ssid in Config.del_ssids:
            self.__delete_existing_connection(ssid)
        if user_data.install_wired:
            self.__delete_existing_wired_connections()
            self.__add_wired_connection(s_8021x)


Messages.quit = "Really quit?"
Messages.username_prompt = "enter your userid"
Messages.enter_password = "enter password"
Messages.enter_import_password = "enter your import password"
Messages.credentials_prompt = "Please enter your credentials:"
Messages.incorrect_password = "incorrect password"
Messages.repeat_password = "repeat your password"
Messages.passwords_differ = "passwords do not match"
Messages.empty_field = "one of the fields was empty"
Messages.installation_finished = "Installation successful"
Messages.cat_dir_exists = "Directory {} exists; some of its files may " \
    "be overwritten"
Messages.cont = "Continue?"
Messages.nm_not_supported = "This NetworkManager version is not " \
    "supported"
Messages.cert_error = "Certificate file not found, looks like a CAT " \
    "error"
Messages.unknown_version = "Unknown version"
Messages.dbus_error = "DBus connection problem, a sudo might help"
Messages.yes = "Y"
Messages.no = "N"
Messages.ok = "OK"
Messages.p12_filter = "personal certificate file (p12 or pfx)"
Messages.all_filter = "All files"
Messages.p12_title = "personal certificate file (p12 or pfx)"
Messages.save_wpa_conf = "DBus module not found - please install " \
    "dbus-python! NetworkManager configuration failed, but we can generate " \
    "a wpa_supplicant configuration file if you wish. Be warned that your " \
    "connection password will be saved in this file as clear text."
Messages.save_wpa_confirm = "Write the file"
Messages.wrong_username_format = "Error: Your username must be of the " \
    "form 'xxx@institutionID' e.g. 'john@example.net'!"
Messages.wrong_realm = "Error: your username must be in the form of " \
    "'xxx@{}'. Please enter the username in the correct format."
Messages.wrong_realm_suffix = "Error: your username must be in the " \
    "form of 'xxx@institutionID' and end with '{}'. Please enter the " \
    "username in the correct format."
Messages.user_cert_missing = "personal certificate file not found"
Messages.wired = "Configure eduroam also on the wired Ethernet?\n\n " \
    "Please be aware that doing so will introduce a connection delay " \
    "lasting up to 30 sec. when you connect to an open wired network."
Config.instname = "University of Gloucestershire"
Config.profilename = ""
Config.url = "https://support.glos.ac.uk/portal/"
Config.email = "itservices@glos.ac.uk"
Config.title = "eduroam CAT"
Config.server_match = "jrs11.glos.ac.uk"
Config.eap_outer = "PEAP"
Config.eap_inner = "MSCHAPV2"
Config.init_info = "This installer has been prepared for {0}\n\nMore " \
    "information and comments:\n\nEMAIL: {1}\nWWW: {2}\n\nInstaller created " \
    "with software from the GEANT project."
Config.init_confirmation = "This installer will only work properly if " \
    "you are a member of {0}."
Config.user_realm = "glos.ac.uk"
Config.ssids = ['eduroam']
Config.del_ssids = []
Config.servers = ['DNS:jrs11.glos.ac.uk']
Config.servers_cn = 'jrs11.glos.ac.uk'
Config.use_other_tls_id = False
Config.hint_user_input = True
Config.verify_user_realm_input = True
Config.tou = ""
Config.wired = ""
Config.CA = """-----BEGIN CERTIFICATE-----
MIIF3jCCA8agAwIBAgIQAf1tMPyjylGoG7xkDjUDLTANBgkqhkiG9w0BAQwFADCB
iDELMAkGA1UEBhMCVVMxEzARBgNVBAgTCk5ldyBKZXJzZXkxFDASBgNVBAcTC0pl
cnNleSBDaXR5MR4wHAYDVQQKExVUaGUgVVNFUlRSVVNUIE5ldHdvcmsxLjAsBgNV
BAMTJVVTRVJUcnVzdCBSU0EgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwHhcNMTAw
MjAxMDAwMDAwWhcNMzgwMTE4MjM1OTU5WjCBiDELMAkGA1UEBhMCVVMxEzARBgNV
BAgTCk5ldyBKZXJzZXkxFDASBgNVBAcTC0plcnNleSBDaXR5MR4wHAYDVQQKExVU
aGUgVVNFUlRSVVNUIE5ldHdvcmsxLjAsBgNVBAMTJVVTRVJUcnVzdCBSU0EgQ2Vy
dGlmaWNhdGlvbiBBdXRob3JpdHkwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAwggIK
AoICAQCAEmUXNg7D2wiz0KxXDXbtzSfTTK1Qg2HiqiBNCS1kCdzOiZ/MPans9s/B
3PHTsdZ7NygRK0faOca8Ohm0X6a9fZ2jY0K2dvKpOyuR+OJv0OwWIJAJPuLodMkY
tJHUYmTbf6MG8YgYapAiPLz+E/CHFHv25B+O1ORRxhFnRghRy4YUVD+8M/5+bJz/
Fp0YvVGONaanZshyZ9shZrHUm3gDwFA66Mzw3LyeTP6vBZY1H1dat//O+T23LLb2
VN3I5xI6Ta5MirdcmrS3ID3KfyI0rn47aGYBROcBTkZTmzNg95S+UzeQc0PzMsNT
79uq/nROacdrjGCT3sTHDN/hMq7MkztReJVni+49Vv4M0GkPGw/zJSZrM233bkf6
c0Plfg6lZrEpfDKEY1WJxA3Bk1QwGROs0303p+tdOmw1XNtB1xLaqUkL39iAigmT
Yo61Zs8liM2EuLE/pDkP2QKe6xJMlXzzawWpXhaDzLhn4ugTncxbgtNMs+1b/97l
c6wjOy0AvzVVdAlJ2ElYGn+SNuZRkg7zJn0cTRe8yexDJtC/QV9AqURE9JnnV4ee
UB9XVKg+/XRjL7FQZQnmWEIuQxpMtPAlR1n6BB6T1CZGSlCBst6+eLf8ZxXhyVeE
Hg9j1uliutZfVS7qXMYoCAQlObgOK6nyTJccBz8NUvXt7y+CDwIDAQABo0IwQDAd
BgNVHQ4EFgQUU3m/WqorSs9UgOHYm8Cd8rIDZsswDgYDVR0PAQH/BAQDAgEGMA8G
A1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQEMBQADggIBAFzUfA3P9wF9QZllDHPF
Up/L+M+ZBn8b2kMVn54CVVeWFPFSPCeHlCjtHzoBN6J2/FNQwISbxmtOuowhT6KO
VWKR82kV2LyI48SqC/3vqOlLVSoGIG1VeCkZ7l8wXEskEVX/JJpuXior7gtNn3/3
ATiUFJVDBwn7YKnuHKsSjKCaXqeYalltiz8I+8jRRa8YFWSQEg9zKC7F4iRO/Fjs
8PRF/iKz6y+O0tlFYQXBl2+odnKPi4w2r78NBc5xjeambx9spnFixdjQg3IM8WcR
iQycE0xyNN+81XHfqnHd4blsjDwSXWXavVcStkNr/+XeTWYRUc+ZruwXtuhxkYze
Sf7dNXGiFSeUHM9h4ya7b6NnJSFd5t0dCy5oGzuCr+yDZ4XUmFF0sbmZgIn/f3gZ
XHlKYC6SQK5MNyosycdiyA5d9zZbyuAlJQG03RoHnHcAP9Dc1ew91Pq7P8yF1m9/
qS3fuQL39ZeatTXaw2ewh0qpKJ4jjv9cJ2vhsE/zB+4ALtRZh8tSQZXq9EfX7mRB
VXyNWQKV3WKdwrnuWih0hKWbt5DHDAff9Yk2dDLWKMGwsAvgnEzDHNb842m1R0aB
L6KCq9NjRHDEjf8tM7qtj3u1cIiuPhnPQCjY/MiQu12ZIvVS5ljFH4gxQ+6IHdfG
jjxDah2nGN59PRbxYvnKkKj9
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIGSzCCBDOgAwIBAgIQbU98rTNTd8jG4AHd4uLIjjANBgkqhkiG9w0BAQwFADBf
MQswCQYDVQQGEwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTYwNAYDVQQD
Ey1TZWN0aWdvIFB1YmxpYyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gUm9vdCBSNDYw
HhcNMjEwMzIyMDAwMDAwWhcNMzYwMzIxMjM1OTU5WjBgMQswCQYDVQQGEwJHQjEY
MBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTcwNQYDVQQDEy5TZWN0aWdvIFB1Ymxp
YyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gQ0EgRVYgUjM2MIIBojANBgkqhkiG9w0B
AQEFAAOCAY8AMIIBigKCAYEApduwxkQH5noeb0k4yRXK47Fd+hVkH8twKWQF3FNm
HHShQrOH7S0L3p8Aaf8P7OqojwyZgyqD5o/Sb95N45P/NfmL+lfAOkQ1Bpvz0OcZ
VmwYhMWFYJe8parkz5w9Bk8mn/AtN65hIQF0NqBI6F+23/jzhlpl3E0zKkkUJSfT
dgvwaJvTiPgLQ7CpYyLJvMpgdPHf+nnvA5YJjhae6olh6BRllvRhzKOq0gd60BrO
Aos9QyOfYhUDG3eQovMA9fyiI2qNclCp6DY8hqt55lERoBS/Whza8Cx1bh6q8rTP
nno2uI6FZb2UavIYblyGDamXAW/jv3qsMB42xz/p2mUHg0wQzn/8KAiyu2ZbDs7E
OOwYx0V2ViNsCXGR/GCmJsUNPmhEEXBclOj6qF7rFf7nkST2bokSt9VF1NB1JgRl
djZin1+v2Vm88UEgFxerQPPrPjAEMqDx44vKl22sGWnl+jOyxf/H59DHKbIezrIY
rJpSnA3WEVaiXs1oIRy1ZziNAgMBAAGjggGAMIIBfDAfBgNVHSMEGDAWgBRWc1hk
lfmSGrASKgRieaFAFYghSTAdBgNVHQ4EFgQUmC1eHo/rVPS5/1WVrUzHfqSYrnsw
DgYDVR0PAQH/BAQDAgGGMBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYI
KwYBBQUHAwEGCCsGAQUFBwMCMBoGA1UdIAQTMBEwBgYEVR0gADAHBgVngQwBATBU
BgNVHR8ETTBLMEmgR6BFhkNodHRwOi8vY3JsLnNlY3RpZ28uY29tL1NlY3RpZ29Q
dWJsaWNTZXJ2ZXJBdXRoZW50aWNhdGlvblJvb3RSNDYuY3JsMIGEBggrBgEFBQcB
AQR4MHYwTwYIKwYBBQUHMAKGQ2h0dHA6Ly9jcnQuc2VjdGlnby5jb20vU2VjdGln
b1B1YmxpY1NlcnZlckF1dGhlbnRpY2F0aW9uUm9vdFI0Ni5wN2MwIwYIKwYBBQUH
MAGGF2h0dHA6Ly9vY3NwLnNlY3RpZ28uY29tMA0GCSqGSIb3DQEBDAUAA4ICAQA2
LRCehSXiyw56alKt2aqDwDLEDmyu74lUmDG4rI1Jw3+ivLz+OK3NpE466a8yXu7b
f326wkrrOCF2SVu3ItNjXqsgwXdIM9tapVEKjsEwbjcPUcxNeqzSpLSgHZIVhjJJ
+QtdEL2n1NhDxqewlN+ZKWWBLGB0LA/S7SvCl9s7rsppo97uv6J3h//q4b2SgzHu
KUu80Hofpjp2bILGHy4CqzKzyg3wn9sKFcX6Ufkcea/tuiWhIMPkiQCv5tXsRj+H
n3CZql+wRPbjhNqncCkzrwOBrt7Gov46EHhqMUP/Euf8gSw7X+CzWEUJ0Q+Vn8VL
ZDkiKcMSYMJI+6Trc5tVn9LQLI6tTzwagLhgcVtFpom3PVtEJRPN/d05L0ck7S1b
xPaXcQhKUqdzFd09pt6fLx2vMmylBKXjKosSxjB12KRzLvI2CUUVdpl7OTFA32Fk
+zQC2gJPGmPPCzRMRYfVOEIZxbG0nI9lpYZidLkQ/EyTtJ3JVj7cb3KRe/e1s+Xj
rnHqbUwoizicfogtcKm5giwj74f+Rpr0RRy4xum1bC662fNHRJaTt5ErVR6gHjHM
Zhp+tOeOvohq5XxIMCKuetnwcPeBsOzUBzmUPoxQNRVXEYbwV2rS3t2jJ0Zh/Dnn
O96biaAsEnxbQyu4fvMx6D4J4Zbkc7Zp75T3GE/UjQ==
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIGTDCCBDSgAwIBAgIQOXpmzCdWNi4NqofKbqvjsTANBgkqhkiG9w0BAQwFADBf
MQswCQYDVQQGEwJHQjEYMBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTYwNAYDVQQD
Ey1TZWN0aWdvIFB1YmxpYyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gUm9vdCBSNDYw
HhcNMjEwMzIyMDAwMDAwWhcNMzYwMzIxMjM1OTU5WjBgMQswCQYDVQQGEwJHQjEY
MBYGA1UEChMPU2VjdGlnbyBMaW1pdGVkMTcwNQYDVQQDEy5TZWN0aWdvIFB1Ymxp
YyBTZXJ2ZXIgQXV0aGVudGljYXRpb24gQ0EgRFYgUjM2MIIBojANBgkqhkiG9w0B
AQEFAAOCAY8AMIIBigKCAYEAljZf2HIz7+SPUPQCQObZYcrxLTHYdf1ZtMRe7Yeq
RPSwygz16qJ9cAWtWNTcuICc++p8Dct7zNGxCpqmEtqifO7NvuB5dEVexXn9RFFH
12Hm+NtPRQgXIFjx6MSJcNWuVO3XGE57L1mHlcQYj+g4hny90aFh2SCZCDEVkAja
EMMfYPKuCjHuuF+bzHFb/9gV8P9+ekcHENF2nR1efGWSKwnfG5RawlkaQDpRtZTm
M64TIsv/r7cyFO4nSjs1jLdXYdz5q3a4L0NoabZfbdxVb+CUEHfB0bpulZQtH1Rv
38e/lIdP7OTTIlZh6OYL6NhxP8So0/sht/4J9mqIGxRFc0/pC8suja+wcIUna0HB
pXKfXTKpzgis+zmXDL06ASJf5E4A2/m+Hp6b84sfPAwQ766rI65mh50S0Di9E3Pn
2WcaJc+PILsBmYpgtmgWTR9eV9otfKRUBfzHUHcVgarub/XluEpRlTtZudU5xbFN
xx/DgMrXLUAPaI60fZ6wA+PTAgMBAAGjggGBMIIBfTAfBgNVHSMEGDAWgBRWc1hk
lfmSGrASKgRieaFAFYghSTAdBgNVHQ4EFgQUaMASFhgOr872h6YyV6NGUV3LBycw
DgYDVR0PAQH/BAQDAgGGMBIGA1UdEwEB/wQIMAYBAf8CAQAwHQYDVR0lBBYwFAYI
KwYBBQUHAwEGCCsGAQUFBwMCMBsGA1UdIAQUMBIwBgYEVR0gADAIBgZngQwBAgEw
VAYDVR0fBE0wSzBJoEegRYZDaHR0cDovL2NybC5zZWN0aWdvLmNvbS9TZWN0aWdv
UHVibGljU2VydmVyQXV0aGVudGljYXRpb25Sb290UjQ2LmNybDCBhAYIKwYBBQUH
AQEEeDB2ME8GCCsGAQUFBzAChkNodHRwOi8vY3J0LnNlY3RpZ28uY29tL1NlY3Rp
Z29QdWJsaWNTZXJ2ZXJBdXRoZW50aWNhdGlvblJvb3RSNDYucDdjMCMGCCsGAQUF
BzABhhdodHRwOi8vb2NzcC5zZWN0aWdvLmNvbTANBgkqhkiG9w0BAQwFAAOCAgEA
YtOC9Fy+TqECFw40IospI92kLGgoSZGPOSQXMBqmsGWZUQ7rux7cj1du6d9rD6C8
ze1B2eQjkrGkIL/OF1s7vSmgYVafsRoZd/IHUrkoQvX8FZwUsmPu7amgBfaY3g+d
q1x0jNGKb6I6Bzdl6LgMD9qxp+3i7GQOnd9J8LFSietY6Z4jUBzVoOoz8iAU84OF
h2HhAuiPw1ai0VnY38RTI+8kepGWVfGxfBWzwH9uIjeooIeaosVFvE8cmYUB4TSH
5dUyD0jHct2+8ceKEtIoFU/FfHq/mDaVnvcDCZXtIgitdMFQdMZaVehmObyhRdDD
4NQCs0gaI9AAgFj4L9QtkARzhQLNyRf87Kln+YU0lgCGr9HLg3rGO8q+Y4ppLsOd
unQZ6ZxPNGIfOApbPVf5hCe58EZwiWdHIMn9lPP6+F404y8NNugbQixBber+x536
WrZhFZLjEkhp7fFXf9r32rNPfb74X/U90Bdy4lzp3+X1ukh1BuMxA/EEhDoTOS3l
7ABvc7BYSQubQ2490OcdkIzUh3ZwDrakMVrbaTxUM2p24N6dB+ns2zptWCva6jzW
r8IWKIMxzxLPv5Kt3ePKcUdvkBU/smqujSczTzzSjIoR5QqQA6lN1ZRSnuHIWCvh
JEltkYnTAH41QJ6SAWO66GrrUESwN/cgZzL4JLEqz1Y=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIGlTCCBH2gAwIBAgIRANJ/u8HeNZ5SFq1hSVhgmcQwDQYJKoZIhvcNAQEMBQAw
gYgxCzAJBgNVBAYTAlVTMRMwEQYDVQQIEwpOZXcgSmVyc2V5MRQwEgYDVQQHEwtK
ZXJzZXkgQ2l0eTEeMBwGA1UEChMVVGhlIFVTRVJUUlVTVCBOZXR3b3JrMS4wLAYD
VQQDEyVVU0VSVHJ1c3QgUlNBIENlcnRpZmljYXRpb24gQXV0aG9yaXR5MB4XDTIx
MDMyMjAwMDAwMFoXDTM4MDExODIzNTk1OVowXzELMAkGA1UEBhMCR0IxGDAWBgNV
BAoTD1NlY3RpZ28gTGltaXRlZDE2MDQGA1UEAxMtU2VjdGlnbyBQdWJsaWMgU2Vy
dmVyIEF1dGhlbnRpY2F0aW9uIFJvb3QgUjQ2MIICIjANBgkqhkiG9w0BAQEFAAOC
Ag8AMIICCgKCAgEAk77VNlJ12AEjoBxHQknuY7a3If3EldVIKyZ8FFMQ2nn9K7ct
pNQs+uoy3UnCub0PSD17WphUr55dMXRPB/xQId2kz2hPGxJjbSWZTCqZ80gwYfqB
fB6nCErcPiscHxhMcao1jK34bug7StnllALWiYQTqm3ITzPMUJY3kjPcX4jnn1TZ
SPCYQ9Zm/Z8XOEPFAVEL1+MjDxRdWxTnS77d9MjaAzfR1jmhIVEwg7Bt1zBOlluR
8HAkq79FgWRDDb0hOi886Z4NyyC1QifM2m+b7mQwkDnNk2WBITG1I1AzNyLjOO34
MTDMRf5i+dFdMnlCh99qzFYZQE3Oqrv5tXZJlPEn+JGlg+UGs2MOgNzgElWApjtm
tDmHLcjw0NEU6eQNTQ72XVdyxTscR1ad4tX7gWGMzE2AkDRbt9cUddzYBEifwMEo
iLTpHMqnsfFWt3tJTFnlIBWohAIp+jiUaZpJBo/NH3kUFxIMg3reH7GX7vmXeCik
yESS6X0mBaZYcpt5E9gRX67FOGI0aLKGMI74kGGeMmz1BzbNokxu7Io27fLmmRVE
cMN8vJw5wLTha/eDJSNX2RKA5UnwdQ/vjescm1QotCE8/HwK/+97a3X/ix2gGQWr
+vgrgULoOLq7+6r9PeDzyt9Ol5cp7fMYVumllqy9w5CYsuD5otSmR0N8bc8CAwEA
AaOCASAwggEcMB8GA1UdIwQYMBaAFFN5v1qqK0rPVIDh2JvAnfKyA2bLMB0GA1Ud
DgQWBBRWc1hklfmSGrASKgRieaFAFYghSTAOBgNVHQ8BAf8EBAMCAYYwDwYDVR0T
AQH/BAUwAwEB/zAdBgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwEQYDVR0g
BAowCDAGBgRVHSAAMFAGA1UdHwRJMEcwRaBDoEGGP2h0dHA6Ly9jcmwudXNlcnRy
dXN0LmNvbS9VU0VSVHJ1c3RSU0FDZXJ0aWZpY2F0aW9uQXV0aG9yaXR5LmNybDA1
BggrBgEFBQcBAQQpMCcwJQYIKwYBBQUHMAGGGWh0dHA6Ly9vY3NwLnVzZXJ0cnVz
dC5jb20wDQYJKoZIhvcNAQEMBQADggIBADpvBIlq7bMU0cFDT/9P9+BsgCkRgQs0
S6Bf7vJSlWMHwby0VGvxCS0hrbi0K2BINZbEbsVsgpQq04431yyoVn3Hldorgq24
RldRDOOipEZDTFB9wC9HYt1thHF00XeG2C8KC1plwoEzKAIhPvefI/C3cT0CfTXJ
uFjUbKIgSwjNjw6YHtLgoy/hd5+JLUlLco/gzFX/qWbT7tEquOMYpsNKWZj8TLqP
q6zMiG4Na6feEZte6YPXGrMWlTWN341vDedc+yxQqSug79HJUQcOZs7KyDWztmae
QxsPE49UV/8XwrfZtZaYyrs4FpD94Z4Q8dzXGL8+qEJjxgcza7W6PROaClubavd1
VKPm8+aCW77u7SxpR2TFGL6kPdxsKyFijpcunR5V79sUyROfNdzjrAcFWZXK8sbb
9FlnwuVG677JLv+ZVTX5AxLvW5OB4zt5uS+zB62wJ/Wv+jXGAttSAcJec4iFgCWH
Rvdi/jJoSzRLa3nEzx6pFIzclSCnh0u1xCeLcUBypSiPga8W+6PkuoyQq8U9qs9E
oxG5NvrvlyshwUS9yvcZRGw7Ljlx4jJH/BhIPR8kIBCQj1vna9TziZOrw1Of8hDU
bHKFG9Pm8Dp2vbjz/2JH39qvxshPKVllGfq+5klPm7yZRUYTiCMAbqwNdL/nsqF2
Rnnyp58XRStJ
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIGlTCCBH2gAwIBAgIRANJ/u8HeNZ5SFq1hSVhgmcQwDQYJKoZIhvcNAQEMBQAw
gYgxCzAJBgNVBAYTAlVTMRMwEQYDVQQIEwpOZXcgSmVyc2V5MRQwEgYDVQQHEwtK
ZXJzZXkgQ2l0eTEeMBwGA1UEChMVVGhlIFVTRVJUUlVTVCBOZXR3b3JrMS4wLAYD
VQQDEyVVU0VSVHJ1c3QgUlNBIENlcnRpZmljYXRpb24gQXV0aG9yaXR5MB4XDTIx
MDMyMjAwMDAwMFoXDTM4MDExODIzNTk1OVowXzELMAkGA1UEBhMCR0IxGDAWBgNV
BAoTD1NlY3RpZ28gTGltaXRlZDE2MDQGA1UEAxMtU2VjdGlnbyBQdWJsaWMgU2Vy
dmVyIEF1dGhlbnRpY2F0aW9uIFJvb3QgUjQ2MIICIjANBgkqhkiG9w0BAQEFAAOC
Ag8AMIICCgKCAgEAk77VNlJ12AEjoBxHQknuY7a3If3EldVIKyZ8FFMQ2nn9K7ct
pNQs+uoy3UnCub0PSD17WphUr55dMXRPB/xQId2kz2hPGxJjbSWZTCqZ80gwYfqB
fB6nCErcPiscHxhMcao1jK34bug7StnllALWiYQTqm3ITzPMUJY3kjPcX4jnn1TZ
SPCYQ9Zm/Z8XOEPFAVEL1+MjDxRdWxTnS77d9MjaAzfR1jmhIVEwg7Bt1zBOlluR
8HAkq79FgWRDDb0hOi886Z4NyyC1QifM2m+b7mQwkDnNk2WBITG1I1AzNyLjOO34
MTDMRf5i+dFdMnlCh99qzFYZQE3Oqrv5tXZJlPEn+JGlg+UGs2MOgNzgElWApjtm
tDmHLcjw0NEU6eQNTQ72XVdyxTscR1ad4tX7gWGMzE2AkDRbt9cUddzYBEifwMEo
iLTpHMqnsfFWt3tJTFnlIBWohAIp+jiUaZpJBo/NH3kUFxIMg3reH7GX7vmXeCik
yESS6X0mBaZYcpt5E9gRX67FOGI0aLKGMI74kGGeMmz1BzbNokxu7Io27fLmmRVE
cMN8vJw5wLTha/eDJSNX2RKA5UnwdQ/vjescm1QotCE8/HwK/+97a3X/ix2gGQWr
+vgrgULoOLq7+6r9PeDzyt9Ol5cp7fMYVumllqy9w5CYsuD5otSmR0N8bc8CAwEA
AaOCASAwggEcMB8GA1UdIwQYMBaAFFN5v1qqK0rPVIDh2JvAnfKyA2bLMB0GA1Ud
DgQWBBRWc1hklfmSGrASKgRieaFAFYghSTAOBgNVHQ8BAf8EBAMCAYYwDwYDVR0T
AQH/BAUwAwEB/zAdBgNVHSUEFjAUBggrBgEFBQcDAQYIKwYBBQUHAwIwEQYDVR0g
BAowCDAGBgRVHSAAMFAGA1UdHwRJMEcwRaBDoEGGP2h0dHA6Ly9jcmwudXNlcnRy
dXN0LmNvbS9VU0VSVHJ1c3RSU0FDZXJ0aWZpY2F0aW9uQXV0aG9yaXR5LmNybDA1
BggrBgEFBQcBAQQpMCcwJQYIKwYBBQUHMAGGGWh0dHA6Ly9vY3NwLnVzZXJ0cnVz
dC5jb20wDQYJKoZIhvcNAQEMBQADggIBADpvBIlq7bMU0cFDT/9P9+BsgCkRgQs0
S6Bf7vJSlWMHwby0VGvxCS0hrbi0K2BINZbEbsVsgpQq04431yyoVn3Hldorgq24
RldRDOOipEZDTFB9wC9HYt1thHF00XeG2C8KC1plwoEzKAIhPvefI/C3cT0CfTXJ
uFjUbKIgSwjNjw6YHtLgoy/hd5+JLUlLco/gzFX/qWbT7tEquOMYpsNKWZj8TLqP
q6zMiG4Na6feEZte6YPXGrMWlTWN341vDedc+yxQqSug79HJUQcOZs7KyDWztmae
QxsPE49UV/8XwrfZtZaYyrs4FpD94Z4Q8dzXGL8+qEJjxgcza7W6PROaClubavd1
VKPm8+aCW77u7SxpR2TFGL6kPdxsKyFijpcunR5V79sUyROfNdzjrAcFWZXK8sbb
9FlnwuVG677JLv+ZVTX5AxLvW5OB4zt5uS+zB62wJ/Wv+jXGAttSAcJec4iFgCWH
Rvdi/jJoSzRLa3nEzx6pFIzclSCnh0u1xCeLcUBypSiPga8W+6PkuoyQq8U9qs9E
oxG5NvrvlyshwUS9yvcZRGw7Ljlx4jJH/BhIPR8kIBCQj1vna9TziZOrw1Of8hDU
bHKFG9Pm8Dp2vbjz/2JH39qvxshPKVllGfq+5klPm7yZRUYTiCMAbqwNdL/nsqF2
Rnnyp58XRStJ
-----END CERTIFICATE-----
"""


if __name__ == '__main__':
    run_installer()
