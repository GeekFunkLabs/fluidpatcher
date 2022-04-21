#!/bin/bash

installdir=""
UPDATED=false
UPGRADE=false
PYTHON_PKG=""
ASK_TO_REBOOT=false

yesno() {
    read -r -p "$1 ([y]/n) " response < /dev/tty
    if [[ $response =~ ^(no|n|N)$ ]]; then
        false
    else
        true
    fi
}

noyes() {
    read -r -p "$1 (y/[n]) " response < /dev/tty
    if [[ $response =~ ^(yes|y|Y)$ ]]; then
        false
    else
        true
    fi
}

query() {
    read -r -p "$1 [$2] " response < /dev/tty
    if [[ $response == "" ]]; then
        response=$2
    fi
}

success() {
    echo -e "$(tput setaf 2)$1$(tput sgr0)"
}

inform() {
    echo -e "$(tput setaf 6)$1$(tput sgr0)"
}

warning() {
    echo -e "$(tput setaf 3)$1$(tput sgr0)"
}

failout() {
    echo -e "$(tput setaf 1)$1$(tput sgr0)"
    exit 1
}

sysupdate() {
    if ! $UPDATED || $UPGRADE; then
        echo "Updating apt indexes..."
        if { sudo apt-get update 2>&1 || echo E: update failed; } | grep '^[WE]:'; then
            warning "Updating incomplete"
        fi
        sleep 3
        UPDATED=true
        if $UPGRADE; then
            echo "Upgrading your system..."
            if { sudo DEBIAN_FRONTEND=noninteractive apt-get -y upgrade --with-new-pkgs 2>&1 \
                || echo E: upgrade failed; } | grep '^[WE]:'; then
                warning "Encountered problems during upgrade"
            fi
            sudo apt-get clean && sudo apt-get autoclean
            sudo apt-get -qqy autoremove
            UPGRADE=false
        fi
    fi
}

apt_pkg_install() {
    APT_CHK=$(dpkg-query -W -f='${Status}\n' "$1" 2> /dev/null | grep "install ok installed")
    if [[ $APT_CHK == "" ]]; then
        sysupdate
        echo "Installing package $1..."
        if { sudo DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install "$1" 2>&1 \
            || echo E: install failed; } | grep '^[WE]:'; then
            if [[ $2 == "required" ]]; then
                failout "Problems installing $1!"
            else
                warning "Problems installing $1!"
            fi
        fi
    fi
}

pip_install() {
    if [[ $PYTHON_PKG == "" ]]; then
        PYTHON_PKG=$(pip3 list 2> /dev/null)
    fi
    if ! [[ $PYTHON_PKG =~ "$1" ]]; then
        echo "Installing Python module $1..."
        if ! { sudo -H pip3 install "$1"; } then
            if [[ $2 == "required" ]]; then
                failout "Failed to install $1!"
            else
                warning "Failed to install $1!"
            fi
        fi
    fi
}


sleep 1 # give curl time to print info

## get options from user

RED='\033[0;31m'
YEL='\033[1;33m'
NC='\033[0m'
echo -e "
 ${YEL}           o
     o───┐  │  o
      ${RED}___${YEL}│${RED}__${YEL}│${RED}__${YEL}│${RED}___
     /             \  ${YEL}o   ${NC}SquishBox/Headless Pi Synth Installer
 ${YEL}o───${RED}┤  ${NC}_________  ${RED}│  ${YEL}│     ${NC}by GEEK FUNK LABS
     ${RED}│ ${NC}│ █ │ █ █ │ ${RED}├${YEL}──┘     ${NC}geekfunklabs.com
     ${RED}│ ${NC}│ █ │ █ █ │ ${RED}│
     \_${NC}│_│_│_│_│_│${RED}_/${NC}
"
inform "This script installs/updates software and optional extras
for the SquishBox or headless Raspberry Pi synth."
warning "Always be careful when running scripts and commands copied
from the internet. Ensure they are from a trusted source."
echo "If you want to see what this script does before running it,
hit ctrl-C and enter 'curl -L git.io/squishbox | more'
View the full source code at
https://github.com/albedozero/fluidpatcher
Report issues with this script at
https://github.com/albedozero/fluidpatcher/issues
"

ENVCHECK=true
if test -f /etc/os-release; then
    if ! { uname -a | grep -q "raspberrypi"; } then
        ENVCHECK=false
    fi
    versioncode=`sed -n '/^VERSION_CODENAME=/s|^.*=||p' /etc/os-release`
    if ! [[ $versioncode =~ (bullseye) ]]; then
        ENVCHECK=false
    fi
fi
if ! ($ENVCHECK); then
    warning "These scripts are designed to run on Raspberry Pi OS (Bullseye),"
    warning "which does not appear to be the case here. YMMV!"
    if noyes "Proceed anyway?"; then
        exit 1
    fi
fi

query "Install location" $HOME; installdir=$response
if test -f "$installdir/patcher/__init__.py"; then
    FP_VER=`sed -n '/^VERSION/s|[^0-9\.]*||gp' $installdir/patcher/__init__.py`
    echo "Installed FluidPatcher is version $FP_VER"
fi
NEW_FP_VER=`curl -s https://github.com/albedozero/fluidpatcher/releases/latest | sed -e 's|.*tag/v||' -e 's|">redirected.*||'`
if yesno "Install/update FluidPatcher version $NEW_FP_VER?"; then
    update="yes"
fi

if command -v fluidsynth > /dev/null; then
    INST_VER=`fluidsynth --version | sed -n '/runtime version/s|[^0-9\.]*||gp'`
    echo "Installed FluidSynth is version $INST_VER"
else
    PKG_VER=`apt-cache policy fluidsynth | sed -n '/Candidate:/s/  Candidate: //p'`
    echo "FluidSynth version $PKG_VER will be installed"
fi
BUILD_VER=`curl -s https://github.com/FluidSynth/fluidsynth/releases/latest | sed -e 's|.*tag/v||' -e 's|">redirected.*||'`
if yesno "Compile and install FluidSynth $BUILD_VER from source?"; then
    compile="yes"
fi

if yesno "OK to upgrade your system (if possible)?"; then
    UPGRADE=true
fi

IFS=$'\n'
AUDIOCARDS=(`aplay -l | grep ^card | cut -d' ' -f 3`)
defcard=0
defscript=2
echo "Which audio output would you like to use?"
echo "  0. No change"
echo "  1. Default"
i=2
for dev in ${AUDIOCARDS[@]}; do
    echo "  $i. $dev"
	if [[ $dev == "Headphones" ]]; then
		defcard=$i
	fi
    ((i+=1))
done
i=2
for dev in ${AUDIOCARDS[@]}; do
	if [[ $dev == "sndrpihifiberry" ]]; then
		defcard=$i
		defscript=1
	fi
    ((i+=1))
done
query "Choose" $defcard; audiosetup=$response

echo "What script should be run on startup?"
echo "  0. No change"
echo "  1. squishbox.py"
echo "  2. headlesspi.py"
echo "  3. Nothing"
query "Choose" $defscript; startup=$response
if [[ $startup == 1 ]]; then
    squishbox_pkg="required"
elif [[ $startup == 2 ]]; then
    echo "Set up controls for headless pi:"
    query "    MIDI channel for controls" "use default"; ctrls_channel=$response
    query "    Next patch button CC" "use default"; incpatch=$response
    query "    Previous patch button CC" "use default"; decpatch=$response
    query "    Bank change button CC" "use default"; bankinc=$response
fi

if yesno "Set up web-based file manager?"; then
    filemgr="yes"
    echo "  Please create a user name and password."
    read -r -p "    username: " fmgr_user < /dev/tty
    read -r -p "    password: " password < /dev/tty
    fmgr_hash=`wget -qO- geekfunklabs.com/passhash.php?password=$password`
fi

if yesno "Download and install ~400MB of additional soundfonts?"; then
    soundfonts="yes"
fi

echo ""
if ! yesno "Option selection complete. Proceed with installation?"; then
    exit 1
fi
warning "\nThis may take some time ... go make some coffee.\n"


## do things

# friendly permissions for web file manager
umask 002 
# desktop distros play an audio message when first booting to setup; this disables it
sudo mv -f /etc/xdg/autostart/piwiz.desktop /etc/xdg/autostart/piwiz.disabled 2> /dev/null
# add user to audio group
sudo usermod -a -G audio $USER
# allow JACK to grant self-connect requests
if ! grep -q "export JACK_NO_AUDIO_RESERVATION=1" $HOME/.profile; then
    echo "export JACK_NO_AUDIO_RESERVATION=1" >> $HOME/.profile
fi


# get dependencies
inform "Installing/Updating required software..."
if $UPGRADE; then sysupdate; fi
apt_pkg_install "python3-pip" required
apt_pkg_install "fluid-soundfont-gm" required
apt_pkg_install "jackd2" required
# allow JACK to set real-time priority for audio
sudo mv /etc/security/limits.d/audio.conf.disabled /etc/security/limits.d/audio.conf 2> /dev/null
apt_pkg_install "ladspa-sdk"
apt_pkg_install "tap-plugins"
apt_pkg_install "wah-plugins"
pip_install "oyaml" required
pip_install "RPi.GPIO" $squishbox_pkg
pip_install "RPLCD" $squishbox_pkg

# install/update fluidpatcher
if [[ $update == "yes" ]]; then
    inform "Installing/Updating FluidPatcher version $NEW_FP_VER ..."
    rm -rf fluidpatcher
    fptemp=`mktemp -dp .`
    wget -qO- https://github.com/albedozero/fluidpatcher/tarball/master | tar -xzC $fptemp
    cd $fptemp/albedozero-fluidpatcher-*
	find . -type d -exec mkdir -p $installdir/{} \;
	find . -type f ! -name "*.yaml" ! -name "hw_overlay.py" -exec cp -f {} $installdir/{} \;
	find . -type f -name "hw_overlay.py" -exec cp -n {} $installdir/{} \;
	find . -type f -name "*.yaml" -exec cp -n {} $installdir/{} \;        
    cd ../..
    rm -rf $fptemp
    ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 $installdir/SquishBox/sf2/
fi

# install/compile fluidsynth
if [[ $compile == "yes" ]]; then
    inform "Compiling latest FluidSynth from source..."
    if grep -q "#deb-src" /etc/apt/sources.list; then
        sudo sed -i "/^#deb-src/s|#||" /etc/apt/sources.list
    fi
    UPDATED=false
    apt_pkg_install "libjack-jackd2-dev"
    echo "Getting build dependencies..."
    if { sudo DEBIAN_FRONTEND=noninteractive apt-get build-dep fluidsynth -y --no-install-recommends 2>&1 \
        || echo E: install failed; } | grep '^[WE]:'; then
        warning "Couldn't get all dependencies!"
    fi
    fstemp=`mktemp -dp .`
    wget -qO- https://github.com/FluidSynth/fluidsynth/tarball/master | tar -xzC $fstemp
    builddir=`ls -d $fstemp/FluidSynth-fluidsynth-*`/build
    mkdir $builddir
    cd $builddir
    echo "Configuring..."
    cmake ..
    echo "Compiling..."
    make
    if ! { sudo make install; } then
        warning "Unable to compile/install FluidSynth $BUILD_VER"
    fi
    sudo ldconfig
    cd ../../..
    rm -rf $fstemp
elif [[ ! $INST_VER ]]; then
    apt_pkg_install "fluidsynth" required
fi

# set up audio
if (( $audiosetup > 0 )); then
    inform "Setting up audio..."
    echo "/usr/bin/jackd --silent --realtime -d alsa --softmode --playback -S" > ~/.jackdrc
    if (( $audiosetup > 1 )); then
        AUDIO=${AUDIOCARDS[$audiosetup-2]}
        if [[ $AUDIO == "Headphones" ]]; then
            echo "/usr/bin/jackd --silent --realtime -d alsa --softmode --playback -S -i 0 -o 2 \\
--device hw:Headphones --period 444 --nperiods 3 --rate 22050" > ~/.jackdrc
        else
            echo "/usr/bin/jackd --silent --realtime -d alsa --softmode --playback -S \\
--device hw:$AUDIO --period 64 --nperiods 3 --rate 44100" > ~/.jackdrc
        fi
    fi
fi

# set up services
if [[ $startup == "1" ]]; then
    inform "Enabling SquishBox startup service..."
    chmod a+x $installdir/squishbox.py
    cat <<EOF | sudo tee /etc/systemd/system/squishbox.service
[Unit]
Description=SquishBox
After=local-fs.target

[Service]
Type=simple
ExecStart=$installdir/squishbox.py
User=$USER
WorkingDirectory=$installdir
Environment="JACK_NO_AUDIO_RESERVATION=1"
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl enable squishbox.service
    ASK_TO_REBOOT=true
elif [[ $startup == "2" ]]; then
    inform "Enabling headless Pi synth startup service..."
    chmod a+x $installdir/headlesspi.py
    cat <<EOF | sudo tee /etc/systemd/system/squishbox.service
[Unit]
Description=Headless Pi Synth
After=local-fs.target

[Service]
Type=simple
ExecStart=$installdir/headlesspi.py
User=$USER
WorkingDirectory=$installdir
Environment="JACK_NO_AUDIO_RESERVATION=1"
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl enable squishbox.service
    if [[ $decpatch != "use default" ]]; then
        sed -i "/^DEC_PATCH/s|[0-9]\+|$decpatch|" $installdir/headlesspi.py; fi
    if [[ $incpatch != "use default" ]]; then
        sed -i "/^INC_PATCH/s|[0-9]\+|$incpatch|" $installdir/headlesspi.py; fi
    if [[ $bankinc != "use default" ]]; then
        sed -i "/^BANK_INC/s|[0-9]\+|$bankinc|" $installdir/headlesspi.py; fi
    if [[ $ctrls_channel != "use default" ]]; then
        sed -i "/^CTRLS_MIDI_CHANNEL/s|[0-9]\+|$ctrls_channel|" $installdir/headlesspi.py; fi
    ASK_TO_REBOOT=true
elif [[ $startup == "3" ]]; then
    inform "Disabling startup service..."
    sudo systemctl disable squishbox.service
    ASK_TO_REBOOT=true
fi

if [[ $filemgr == "yes" ]]; then
    # set up web server, install tinyfilemanager
    inform "Setting up web-based file manager..."
    sysupdate
    apt_pkg_install "nginx"
    apt_pkg_install "php-fpm"
    phpver=`apt-cache policy php-fpm | sed -n '/Installed:/s/.*://p' | sed 's/[^0-9\.].*//'`
    # enable php in nginx
    cat <<EOF | sudo tee /etc/nginx/sites-available/default
server {
        listen 80 default_server;
        listen [::]:80 default_server;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name _;
        location / {
                try_files \$uri \$uri/ =404;
        }
        location ~ \.php\$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/run/php/php$phpver-fpm.sock;
        }
}
EOF
    # some tweaks to allow uploading bigger files
    if grep -q "client_max_body_size" /etc/nginx/nginx.conf; then
        sudo sed -i "/client_max_body_size/cclient_max_body_size 900M;" /etc/nginx/nginx.conf
    else
        sudo sed -i "/^http {/aclient_max_body_size 900M;" /etc/nginx/nginx.conf
    fi
    sudo sed -i "/upload_max_filesize/cupload_max_filesize = 900M" /etc/php/$phpver/fpm/php.ini
    sudo sed -i "/post_max_size/cpost_max_size = 999M" /etc/php/$phpver/fpm/php.ini
    # set permissions and umask to avoid permissions problems
    sudo usermod -a -G $USER www-data
    sudo chmod -R g+rw $installdir/SquishBox
    if grep -q "UMask" /lib/systemd/system/php$phpver-fpm.service; then
        sudo sed -i "/UMask/cUMask=0002" /lib/systemd/system/php$phpver-fpm.service
    else
        sudo sed -i "/\[Service\]/aUMask=0002" /lib/systemd/system/php$phpver-fpm.service
    fi
    # install and configure [tinyfilemanager](https://tinyfilemanager.github.io)
    wget -q https://raw.githubusercontent.com/prasathmani/tinyfilemanager/master/tinyfilemanager.php
    sed -i "/define('APP_TITLE'/cdefine('APP_TITLE', 'SquishBox Manager');" tinyfilemanager.php
    sed -i "/'admin' =>/d;/'user' =>/d" tinyfilemanager.php
    sed -i "/\$auth_users =/a    '$fmgr_user' => '$fmgr_hash'" tinyfilemanager.php
    sed -i "/\$theme =/c\$theme = 'dark';" tinyfilemanager.php
    sed -i "0,/root_path =/s|root_path = .*|root_path = '$installdir/SquishBox';|" tinyfilemanager.php
    sed -i "0,/favicon_path =/s|favicon_path = .*|favicon_path = 'gfl_logo.png';|" tinyfilemanager.php
    sed -i '/aceMode/s|,"yaml":"YAML"||' tinyfilemanager.php
    sed -i 's|"aceMode":{|&"yaml":"YAML",|' tinyfilemanager.php
    sudo mv -f tinyfilemanager.php /var/www/html/index.php
    wget -q https://geekfunklabs.com/gfl_logo.png
    sudo mv -f gfl_logo.png /var/www/html/
    ASK_TO_REBOOT=true
fi

if [[ $soundfonts == "yes" ]]; then
    # download extra soundfonts
    inform "Downloading free soundfonts..."
    wget -qO- --show-progress https://geekfunklabs.com/squishbox_soundfonts.tar.gz | tar -xzC $installdir/SquishBox --skip-old-files
fi

success "Tasks complete!"

if $ASK_TO_REBOOT; then
    warning "\nSome changes made to your system require"
    warning "your computer to reboot to take effect."
    echo
    if yesno "Would you like to reboot now?"; then
        sync && sudo reboot
    fi
fi
