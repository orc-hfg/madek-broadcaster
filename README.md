> Clone of Sender Medienarchiv der Künste by Birk Weiberg  
> https://gitlab.zhdk.ch/birk/madek-broadcaster

Sender Medienarchiv der Künste
==============================

![](https://medienarchiv.zhdk.ch/media/822530be-7300-4332-9049-5ad905ac3df6)

## System installation

Install Ubuntu 16.04 LTS.

In *Settings > System > Details* change the device name to `nipkow`. In *Settings > User* create a main admin user `itz` with automatic login enabled. In *Settings > Brightness & Lock* disable the screen saver.

In the Terminal update the system and change the keyboard layout.

```bash
sudo apt-get update  
sudo apt-get install unattended-upgrades  
setxkbmap ch  
```

Enable automtic security update.

```bash
sudo dpkg-reconfigure unattended-upgrades
```

Install necessary software.

```bash
sudo apt-get install python3-pip python-pyglet virtualenvwrapper git supervisor openssh-server samba-common-bin
```

Add your own public key form remote access to `~/.ssh/authorized_keys`.

## Player installation

Create a virtual environment.

```bash
mkvirtualenv --python=/usr/bin/python3 broadcaster  
echo "source /usr/share/virtualenvwrapper/virtualenvwrapper.sh" >> ~/.bashrc  
echo "workon broadcaster" >> ~/.bashrc  
```

Create a SSH key pair for the machine and add the public key here as a deploy key: [https://gitlab.zhdk.ch/bweiberg/madek-broadcaster/deploy_keys](https://gitlab.zhdk.ch/bweiberg/madek-broadcaster/deploy_keys)

Add 

```bash
host gitlab.zhdk.ch  
      identityfile ~/.ssh/id_rsa  
```

to `~/.ssh/config`.

Clone the repository and install python packages.

```bash
git clone git@gitlab.zhdk.ch:bweiberg/madek-broadcaster.git  
cd madek-broadcaster  
pip3 install -r requirements.txt  
```

Install `libav` from `dependencies/ubuntu/` or [https://libav.org/download/](https://libav.org/download/).

Copy `monitors.xml` (the config file for the screens) to `~/.config/` and change the permissions to `755`.

Duplicate `player/api_access.py.sample` as `player/api_access.py` and change the values of `user` and `password`.

Run the software manually via `python player/main.py`.

## Setting player software up as a `systemd` service

This ensures that the player software starts automatically after startup and possible crashes.

Create directory `~/.config/systemd/user` and copy `service/player.service` there.  
Enable the service: `systemctl --user enable player.service`  
Reload the daemon: `sudo systemctl daemon-reload`  
And restart the service: `sudo systemctl restart player.service`  

## Defining cronjobs to supervise the player and to delete the log file weekly

Via `crontab -e` add:

```bash
SHELL=/bin/bash
USER=itz

* * * * * /home/itz/madek-broadcaster/service/service_check.sh
0 0 * * 1 rm /home/itz/log
```

