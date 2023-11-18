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
        echo "Updating package indexes..."
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
    sysupdate
    echo "Installing package $1..."
    if { sudo DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install "$1" 2>&1 \
        || echo E: install failed; } | grep '^[WE]:'; then
        if [[ ! $2 == "optional" ]]; then
            failout "Problems installing $1!"
        else
            warning "Problems installing $1!"
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
https://github.com/GeekFunkLabs/fluidpatcher
Report issues with this script at
https://github.com/GeekFunkLabs/fluidpatcher/issues

Choose your install options. An empty response will use the [default option].
Setup will begin after all questions are answered.
"

ENVCHECK=true
if test -f /etc/os-release; then
    if ! { grep -q ^Raspberry /proc/device-tree/model; } then
        ENVCHECK=false
    fi
    if ! { grep -q "bullseye\|bookworm" /etc/os-release; } then
        ENVCHECK=false
    fi
fi
if ! ($ENVCHECK); then
    warning "This software is designed for a Raspberry Pi computer"
    warning "running Raspberry Pi OS bullseye or bookworm,"
    warning "which does not appear to be the situation here. YMMV!"
    if noyes "Proceed anyway?"; then
        exit 1
    fi
fi

echo "What are you setting up?"
echo "  1. SquishBox"
echo "  2. Headless Raspberry Pi Synth"
query "Choose" "1"; installtype=$response
AUDIOCARDS=(`cat /proc/asound/cards | sed -n 's/.*\[//;s/ *\].*//p'`)
if [[ $installtype == 1 ]]; then
    if [[ ! " ${AUDIOCARDS[*]} " =~ " sndrpihifiberry " ]]; then
        inform "This script must reboot your computer to activate your sound card."
        inform "Once this is complete, run this script again to continue setup."
        if yesno "Reboot?"; then
			if test -d /boot/firmware; then
				sudo sed -i '$ a\dtoverlay=hifiberry-dac' /boot/firmware/config.txt
			else
				sudo sed -i '$ a\dtoverlay=hifiberry-dac' /boot/config.txt
			fi
            sync; sudo reboot
			exit 0
        fi
    fi
	echo "What version of SquishBox hardware are you using?"
	echo "  v6 - Green PCB with SMT components"
	echo "  v4 - Purple PCB, has 2 resistors and LED"
	echo "  v3 - Purple PCB, has 1 resistor"
	echo "  v2 - Hackaday/perfboard build"
	query "Enter version code" "v6"; hw_version=$response
elif [[ $installtype == 2 ]]; then
    echo "Set up controls for Headless Pi Synth:"
    query "    MIDI channel for controls" "1"; ctrls_channel=$response
    query "    Previous patch momentary CC#" "21"; decpatch=$response
    query "    Next patch momentary CC#" "22"; incpatch=$response
    query "    Bank advance momentary CC#" "23"; bankinc=$response
else
    exit 1
fi

query "Enter install location" $HOME; installdir=$response
if ! [[ -d $installdir ]]; then
    if noyes "'$installdir' does not exist. Create it and proceed?"; then
        exit 1
    else
        mkdir -p $installdir
    fi
fi

if yesno "Install/update synthesizer software?"; then
    install_synth=true
fi

if yesno "Update/upgrade your operating system?"; then
    UPGRADE=true
fi

defcard=0
echo "Which audio output would you like to use?"
echo "  0. No change"
echo "  1. Default"
i=2
for dev in ${AUDIOCARDS[@]}; do
    echo "  $i. $dev"
    if [[ $installtype == 1 && $dev == "sndrpihifiberry" ]]; then
        defcard=$i
    elif [[ $installtype == 2 && $dev == "Headphones" ]]; then
        defcard=$i
    fi
    ((i+=1))
done
query "Choose" $defcard; audiosetup=$response

if yesno "Set up web-based file manager?"; then
    filemgr=true
    echo "  Please create a user name and password."
    read -r -p "    username: " fmgr_user < /dev/tty
    read -r -p "    password: " fmgr_pass < /dev/tty
fi

if yesno "Download and install ~400MB of additional soundfonts?"; then
    soundfonts=true
fi

echo ""
if ! yesno "Option selection complete. Proceed with installation?"; then
    exit 1
fi
warning "\nThis may take some time ... go make some coffee.\n"


## do things

# friendly file permissions for web file manager
umask 002 

if [[ $install_synth ]]; then
    # get dependencies
    inform "Installing/Updating supporting software..."
    sysupdate
    apt_pkg_install "python3-yaml"
	apt_pkg_install "python3-rpi.gpio"
    apt_pkg_install "fluid-soundfont-gm"
    apt_pkg_install "ladspa-sdk" optional
    apt_pkg_install "swh-plugins" optional
    apt_pkg_install "tap-plugins" optional
    apt_pkg_install "wah-plugins" optional

    # install/update fluidpatcher
    FP_VER=`curl -s https://api.github.com/repos/GeekFunkLabs/fluidpatcher/releases/latest | sed -n '/tag_name/s|[^0-9\.]*||gp'`
    inform "Installing/Updating FluidPatcher version $FP_VER ..."
    wget -qO - https://github.com/GeekFunkLabs/fluidpatcher/tarball/master | tar -xzm
    fptemp=`ls -dt GeekFunkLabs-fluidpatcher-* | head -n1`
    cd $fptemp
    find . -type d -exec mkdir -p ../{} \;
    # copy files, but don't overwrite banks, config (i.e. yaml files)
    find . -type f ! -name "*.yaml" ! -name "hw_overlay.py" -exec cp -f {} ../{} \;
    find . -type f -name "*.yaml" -exec cp -n {} ../{} \;
    cd ..
    rm -rf $fptemp
    ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 SquishBox/sf2/ > /dev/null
    gcc -shared assets/patchcord.c -o patchcord.so
    sudo mv -f patchcord.so /usr/lib/ladspa

    # compile/install fluidsynth
    CUR_FS_VER=`fluidsynth --version 2> /dev/null | sed -n '/runtime version/s|[^0-9\.]*||gp'`
	FS_VER='2.3.4'
    if [[ ! $CUR_FS_VER == $FS_VER ]]; then
        inform "Compiling latest FluidSynth from source..."
        echo "Getting build dependencies..."
        if { grep -q ^#deb-src /etc/apt/sources.list; } then
            sudo sed -i "/^#deb-src/s|#||" /etc/apt/sources.list
            UPDATED=false
            sysupdate
        fi
        if { sudo DEBIAN_FRONTEND=noninteractive apt-get build-dep fluidsynth -y --no-install-recommends 2>&1 \
            || echo E: install failed; } | grep '^[WE]:'; then
            warning "Couldn't get all dependencies!"
        fi
        wget -qO - https://github.com/FluidSynth/fluidsynth/archive/refs/tags/v$FS_VER.tar.gz | tar -xzm
        fstemp=`ls -dt fluidsynth-* | head -n1`
        mkdir $fstemp/build
        cd $fstemp/build
        echo "Configuring..."
        cmake ..
        echo "Compiling..."
        make
        if { sudo make install; } then
            sudo ldconfig
        else
            warning "Unable to compile FluidSynth $BUILD_VER - installing from package repository"
            apt_pkg_install "fluidsynth"
        fi
        cd ../..
        rm -rf $fstemp
    fi
fi

# set up audio
if (( $audiosetup > 0 )); then
    inform "Setting up audio..."
    sed -i "/audio.driver/d" $installdir/SquishBox/squishboxconf.yaml
    sed -i "/fluidsettings:/a\  audio.driver: alsa" $installdir/SquishBox/squishboxconf.yaml
    sed -i "/audio.alsa.device/d" $installdir/SquishBox/squishboxconf.yaml
    if (( $audiosetup > 1 )); then
        card=${AUDIOCARDS[$audiosetup-2]}
        sed -i "/audio.driver/a\  audio.alsa.device: hw:$card" $installdir/SquishBox/squishboxconf.yaml
    fi
fi

# set up services
if [[ $installtype == 1 ]]; then
    inform "Enabling SquishBox startup service..."
    chmod a+x $installdir/squishbox.py
    chmod a+x $installdir/lcdsplash.py
    SB_VER=`sed -n '/^__version__/s|[^0-9\.]*||gp' $installdir/squishbox.py`
    sed -i "/^HW_VERSION/cHW_VERSION = '$hw_version'" $installdir/squishbox.py
    sed -i "/^HW_VERSION/cHW_VERSION = '$hw_version'" $installdir/lcdsplash.py
    sed -i "/^SB_VERSION/cSB_VERSION = '$SB_VER'"
    cat <<EOF | sudo tee /etc/systemd/system/squishbox.service
[Unit]
Description=SquishBox
After=local-fs.target

[Service]
Type=simple
ExecStart=$installdir/squishbox.py
User=$USER
WorkingDirectory=$installdir
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    cat <<EOF | sudo tee /etc/systemd/system/lcdsplash.service
[Unit]
Description=LCD Splashscreen
DefaultDependencies=false

[Service]
Type=oneshot
ExecStart=$installdir/lcdsplash.py
Restart=no

[Install]
WantedBy=sysinit.target
EOF
    sudo systemctl enable squishbox.service
    sudo systemctl enable lcdsplash.service
    ASK_TO_REBOOT=true

elif [[ $installtype == 2 ]]; then
    inform "Enabling Headless Pi Synth startup service..."
    chmod a+x $installdir/headlesspi.py
    sed -i "/^CHAN/s|[0-9]\+|$ctrls_channel|" $installdir/headlesspi.py
    sed -i "/^DEC_PATCH/s|[0-9]\+|$decpatch|" $installdir/headlesspi.py
    sed -i "/^INC_PATCH/s|[0-9]\+|$incpatch|" $installdir/headlesspi.py
    sed -i "/^BANK_INC/s|[0-9]\+|$bankinc|" $installdir/headlesspi.py
    cat <<EOF | sudo tee /etc/systemd/system/squishbox.service
[Unit]
Description=Headless Pi Synth
After=local-fs.target

[Service]
Type=simple
ExecStart=$installdir/headlesspi.py
User=$USER
WorkingDirectory=$installdir
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl enable squishbox.service
    ASK_TO_REBOOT=true
fi

if [[ $filemgr ]]; then
    # set up web server, install tinyfilemanager
    inform "Setting up web-based file manager..."
    sysupdate
    apt_pkg_install "nginx"
    apt_pkg_install "php-fpm"
    phpver=`ls -t /etc/php | head -n1`
    fmgr_hash=`php -r "print password_hash('$fmgr_pass', PASSWORD_DEFAULT);"`
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
    sudo sed -i "/client_max_body_size/d" /etc/nginx/nginx.conf
    sudo sed -i "/^http {/aclient_max_body_size 900M;" /etc/nginx/nginx.conf
    sudo sed -i "/upload_max_filesize/cupload_max_filesize = 900M" /etc/php/$phpver/fpm/php.ini
    sudo sed -i "/post_max_size/cpost_max_size = 999M" /etc/php/$phpver/fpm/php.ini
    # set permissions and umask to avoid permissions problems
    sudo usermod -a -G $USER www-data
    sudo chmod -R g+rw $installdir/SquishBox
    sudo sed -i "/UMask/d" /lib/systemd/system/php$phpver-fpm.service
    sudo sed -i "/\[Service\]/aUMask=0002" /lib/systemd/system/php$phpver-fpm.service
    # install and configure tinyfilemanager (https://tinyfilemanager.github.io)
    wget -q https://raw.githubusercontent.com/prasathmani/tinyfilemanager/master/tinyfilemanager.php
    sed -i "/define('APP_TITLE'/cdefine('APP_TITLE', 'SquishBox Manager');" tinyfilemanager.php
    sed -i "/'admin' =>/d;/'user' =>/d" tinyfilemanager.php
    sed -i "/\$auth_users =/a\    '$fmgr_user' => '$fmgr_hash'" tinyfilemanager.php
    sed -i "/\$theme =/c\$theme = 'dark';" tinyfilemanager.php
    sed -i "0,/root_path =/s|root_path = .*|root_path = '$installdir/SquishBox';|" tinyfilemanager.php
    sed -i "0,/favicon_path =/s|favicon_path = .*|favicon_path = 'gfl_logo.png';|" tinyfilemanager.php
    sudo mv -f tinyfilemanager.php /var/www/html/index.php
	sudo cp -f assets/gfl_logo.png /var/www/html/
    ASK_TO_REBOOT=true
fi

if [[ $soundfonts ]]; then
    # download extra soundfonts
    inform "Downloading free soundfonts..."
    wget -qO - --show-progress https://geekfunklabs.com/squishbox_soundfonts.tar.gz | tar -xzC $installdir/SquishBox --skip-old-files
fi

success "Tasks complete!"

if $ASK_TO_REBOOT; then
    warning "\nSome changes made to your system require a restart to take effect."
    echo "  1. Shut down"
    echo "  2. Reboot"
    echo "  3. Exit"
    query "Choose" "1"
    if [[ $response == 1 ]]; then
        sync && sudo poweroff
    elif [[ $response == 2 ]]; then
        sync && sudo reboot
    fi
fi
