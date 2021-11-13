#!/bin/bash

installdir=""
UPDATED=false
UPGRADE=false
PYTHON_PKG=""
ASK_TO_REBOOT=false

promptorno() {
	read -r -p "$1 (y/[n]) " response < /dev/tty
	if [[ $response =~ ^(yes|y|Y)$ ]]; then
		true
	else
		false
	fi
}

promptoryes() {
	read -r -p "$1 ([y]/n) " response < /dev/tty
	if [[ $response =~ ^(no|n|N)$ ]]; then
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
    echo -e "$(tput setaf 1)$1$(tput sgr0)"
}

sysupdate() {
    if ! $UPDATED; then
        echo "Updating apt indexes..."
        sudo apt-get -qq update || { warning "Failed to update apt indexes!" && exit 1; }
        sleep 3
        UPDATED=true
		if $UPGRADE; then
			echo "Upgrading your system..."
			sudo DEBIAN_FRONTEND=noninteractive apt-get -qqy upgrade --with-new-pkgs
			sudo apt-get clean && sudo apt-get autoclean
			sudo apt-get -qqy autoremove
			UPGRADE=false
		fi
    fi
}

apt_pkg_install() {
    APT_CHK=$(dpkg-query -W -f='${Status}\n' "$1" 2> /dev/null | grep "install ok installed")
    if [[ $APT_CHK == "" ]]; then    
        echo "Aptitude is installing $1..."
        sudo DEBIAN_FRONTEND=noninteractive apt-get --no-install-recommends -qqy install "$1" ||
			{ warning "Apt failed to install $1!" && exit 1; }
    fi
}

pip_install() {
    if [[ $PYTHON_PKG == "" ]]; then
        PYTHON_PKG=$(pip3 list 2> /dev/null)
    fi
    if ! [[ $PYTHON_PKG =~ "$1" ]]; then
        echo "Python Package Manager is installing $1..."
        sudo -H pip3 install "$1" || { warning "Pip failed to install $1!" && exit 1; }
    fi
}


sleep 1 # give curl time to print info

## get options from the user

inform "\nThis script installs/updates software and optonal extras"
inform "for the SquishBox or headless Raspberry Pi synth."
warning "Always be careful when running scripts and commands copied"
warning "from the internet. Ensure they are from a trusted source."
echo "If you want to see what this script does before running it,"
echo "hit ctrl-C and enter 'curl -L git.io/squishbox | more'"
echo -e "Report issues with this script at https://github.com/albedozero/fluidpatcher\n"

ENVCHECK=true
if test -f /etc/os-release; then
	if ! grep -q "raspbian" /etc/os-release; then
		ENVCHECK=false
	fi
	versioncode=`sed -n '/^VERSION_CODENAME=/s|^.*=||p' /etc/os-release`
	if ! [[ $versioncode =~ (buster|bullseye) ]]; then
	    ENVCHECK=false
    fi
fi
if ! ($ENVCHECK); then
	warning "These scripts are designed to run on Raspbian Buster or later,"
	warning "which does not appear to be the case here. YMMV!"
	if ! promptorno "Proceed anyway?"; then
		exit 1
	fi
fi

inform "Core software update/install and system settings:"
query "Install location" `echo ~`; installdir=$response
if test -f "$installdir/patcher/__init__.py"; then
	FP_VER=`sed -n '/^VERSION/s|[^0-9\.]*||gp' $installdir/patcher/__init__.py`
	echo "Installed FluidPatcher is version $FP_VER"
fi
NEW_FP_VER=`curl -s https://raw.githubusercontent.com/albedozero/fluidpatcher/master/patcher/__init__.py | sed -n '/^VERSION/s|[^0-9\.]*||gp'`
if promptoryes "Install/update FluidPatcher version $NEW_FP_VER?"; then
	update="yes"
	if promptorno "Overwrite existing banks/settings?"; then
		overwrite="yes"
	fi 
fi

if promptorno "OK to upgrade your system (if possible)?"; then
	UPGRADE=true
fi
echo "Software repositories you are currently using:"
for repo in `sed -n '/^deb /p' /etc/apt/sources.list | cut -d' ' -f2`; do
    echo "  $repo"
done
echo "Some sites may respond too slowly (e.g.  http://raspbian.raspberrypi.org/raspbian),"
echo "causing installation to fail. For this reason, you may want to add a site near you"
echo "from the list at https://www.raspbian.org/RaspbianMirrors"
query "Software repository to add" "none"; mirror=$response

IFS=$'\n'
AUDIOCARDS=(`aplay -l | grep ^card | cut -d' ' -f 3-`)
echo "Which audio output would you like to use?"
echo "  0. No change"
echo "  1. Default"
i=2
for dev in ${AUDIOCARDS[@]}; do
	echo "  $i. ${AUDIOCARDS[$i-2]}"
	((i+=1))
done
query "Choose" "0"; audiosetup=$response

echo "What script should be run on startup?"
echo "  0. No change"
echo "  1. squishbox.py"
echo "  2. headlesspi.py"
echo "  3. Nothing"
query "Choose" "0"; startup=$response
if [[ $startup == 2 ]]; then
	echo -e "Set up controls for headless pi:"
	query "    MIDI channel for controls" "use default"; ctrls_channel=$response
	query "    Next patch button CC" "use default"; incpatch=$response
	query "    Previous patch button CC" "use default"; decpatch=$response
	query "    Patch select knob CC" "use default"; selectpatch=$response
	query "    Bank change button CC" "use default"; bankinc=$response
fi

inform "\nOptional tasks/add-ons:"

if command -v fluidsynth > /dev/null; then
	INST_VER=`fluidsynth --version | sed -n '/runtime version/s|[^0-9\.]*||gp'`
	echo "Installed FluidSynth is version $INST_VER"
else
	PKG_VER=`apt-cache policy fluidsynth | sed -n '/Candidate:/s/  Candidate: //p'`
	echo "FluidSynth version $PKG_VER will be installed"
fi
BUILD_VER=`curl -s https://github.com/FluidSynth/fluidsynth/releases/latest | sed -e 's|.*tag/v||' -e 's|">redirected.*||'`
if promptorno "Compile and install FluidSynth $BUILD_VER from source?"; then
	compile="yes"
fi

if promptorno "Set up web-based file manager?"; then
	filemgr="yes"
	echo "  Please create a user name and password."
	read -r -p "    username: " fmgr_user < /dev/tty
	read -r -p "    password: " password < /dev/tty
	fmgr_hash=`wget -qO- geekfunklabs.com/passhash.php?password=$password`
fi

if promptorno "Download and install ~400MB of additional soundfonts?"; then
	soundfonts="yes"
fi

echo ""
if ! promptoryes "All options chosen. OK to proceed?"; then
	exit 1
fi
warning "\nThis may take some time ... go make some coffee.\n"

## do things

# friendly permissions for web file manager
umask 002 
# desktop distros play an audio message when first booting to setup; this disables it
sudo mv -f /etc/xdg/autostart/piwiz.desktop /etc/xdg/autostart/piwiz.disabled 2> /dev/null

# get dependencies
inform "Installing/Updating required software..."
if [[ $mirror != "none" ]]; then
    echo "deb $mirror $versioncode main contrib non-free rpi" | sudo tee -a /etc/apt/sources.list
    echo "deb-src $mirror $versioncode main contrib non-free rpi" | sudo tee -a /etc/apt/sources.list
fi
sysupdate
apt_pkg_install "git"
apt_pkg_install "python3-pip"
apt_pkg_install "python3-rtmidi"
apt_pkg_install "fluidsynth"
apt_pkg_install "jackd1"
pip_install "oyaml"
pip_install "mido"
pip_install "RPi.GPIO"
pip_install "RPLCD"
sudo usermod -a -G audio pi

if [[ $update == "yes" ]]; then
    inform "Installing/Updating FluidPatcher version $NEW_FP_VER ..."
    rm -rf fluidpatcher
    git clone https://github.com/albedozero/fluidpatcher
	cd fluidpatcher
    if [[ $overwrite == "yes" ]]; then
        find . -type d -exec mkdir -p $installdir/{} \;
        find . -type f ! -name "hw_overlay.py" -exec cp -f {} $installdir/{} \;
        find . -type f -name "hw_overlay.py" -exec cp -n {} $installdir/{} \;
    else
        find . -type d -exec mkdir -p $installdir/{} \;
        find . -type f ! -name "*.yaml" ! -name "hw_overlay.py" -exec cp -f {} $installdir/{} \;
        find . -type f -name "hw_overlay.py" -exec cp -n {} $installdir/{} \;
        find . -type f -name "*.yaml" -exec cp -n {} $installdir/{} \;        
    fi
	cd ..
    rm -rf fluidpatcher
    ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 $installdir/SquishBox/sf2/
fi

# set up audio
if (( $audiosetup > 0 )); then
	inform "Setting up audio..."
	sed -i "/  audio.alsa.device/d" $installdir/SquishBox/squishboxconf.yaml
	echo "/usr/bin/jackd --silent -r -d alsa -s -p 64 -n 3 -r 44100 -P" | sudo tee /etc/jackdrc
	if (( $audiosetup > 1 )); then
		AUDIO=`echo ${AUDIOCARDS[$audiosetup-2]} | cut -d' ' -f 1`
		sed -i "/^fluidsettings:/a\  audio.alsa.device: hw:$AUDIO"  $installdir/SquishBox/squishboxconf.yaml
		echo "/usr/bin/jackd --silent -r -d alsa -d hw:$AUDIO -s -p 64 -n 3 -r 44100 -P" | sudo tee /etc/jackdrc
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
User=pi
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
User=pi
WorkingDirectory=$installdir
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
	if [[ $selectpatch != "use default" ]]; then
		sed -i "/^SELECT_PATCH/s|[0-9]\+|$selectpatch|" $installdir/headlesspi.py; fi
	if [[ $ctrls_channel != "use default" ]]; then
		sed -i "/^CTRLS_MIDI_CHANNEL/s|[0-9]\+|$ctrls_channel|" $installdir/headlesspi.py; fi
    ASK_TO_REBOOT=true
elif [[ $startup == "3" ]]; then
    inform "Disabling startup service..."
    sudo systemctl disable squishbox.service
    ASK_TO_REBOOT=true
fi

if [[ $compile == "yes" ]]; then
    # compile latest FluidSynth
    inform "Compiling latest FluidSynth from source..."
    if grep -q "#deb-src" /etc/apt/sources.list; then
        sudo sed -i "/^#deb-src/s|#||" /etc/apt/sources.list
    fi
    UPDATED=false
    sysupdate
    apt_pkg_install "tap-plugins"
    echo "Getting build dependencies..."
    sudo apt-get build-dep fluidsynth --no-install-recommends --yes
    rm -rf fluidsynth
    git clone https://github.com/FluidSynth/fluidsynth
    mkdir fluidsynth/build
    cd fluidsynth/build
    echo "Configuring..."
    cmake ..
    echo "Compiling..."
    make
    sudo make install
    sudo ldconfig
    cd ../..
    rm -rf fluidsynth
fi

if [[ $filemgr == "yes" ]]; then
    # set up web server, install tinyfilemanager
    inform "Setting up web-based file manager..."
    sysupdate
    apt_pkg_install "nginx"
    apt_pkg_install "php-fpm"
    # enable php in nginx
    cat <<'EOF' | sudo tee /etc/nginx/sites-available/default
server {
        listen 80 default_server;
        listen [::]:80 default_server;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name _;
        location / {
                try_files $uri $uri/ =404;
        }
        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/run/php/php7.3-fpm.sock;
        }
}
EOF
    # some tweaks to allow uploading bigger files
    if grep -q "client_max_body_size" /etc/nginx/nginx.conf; then
        sudo sed -i "/client_max_body_size/cclient_max_body_size 900M;" /etc/nginx/nginx.conf
    else
        sudo sed -i "/^http {/aclient_max_body_size 900M;" /etc/nginx/nginx.conf
    fi
    sudo sed -i "/upload_max_filesize/cupload_max_filesize = 900M" /etc/php/7.3/fpm/php.ini
    sudo sed -i "/post_max_size/cpost_max_size = 999M" /etc/php/7.3/fpm/php.ini
    # set permissions and umask to avoid permissions problems
    sudo usermod -a -G pi www-data
    sudo chmod -R g+rw $installdir/SquishBox
    if grep -q "UMask" /lib/systemd/system/php7.3-fpm.service; then
        sudo sed -i "/UMask/cUMask=0002" /lib/systemd/system/php7.3-fpm.service
    else
        sudo sed -i "/\[Service\]/aUMask=0002" /lib/systemd/system/php7.3-fpm.service
    fi
    # install and configure [tinyfilemanager](https://tinyfilemanager.github.io)
    wget -q raw.githubusercontent.com/prasathmani/tinyfilemanager/master/tinyfilemanager.php
    sed -i "/define('APP_TITLE'/cdefine('APP_TITLE', 'SquishBox Manager');" tinyfilemanager.php
    sed -i "/'admin' =>/d;/'user' =>/d" tinyfilemanager.php
    sed -i "/\$auth_users =/a    '$fmgr_user' => '$fmgr_hash'" tinyfilemanager.php
    sed -i "/\$theme =/c\$theme = 'dark';" tinyfilemanager.php
    sed -i "0,/root_path =/s|root_path = .*|root_path = '$installdir/SquishBox';|" tinyfilemanager.php
    sed -i "0,/favicon_path =/s|favicon_path = .*|favicon_path = 'gfl_logo.png';|" tinyfilemanager.php
    sed -i '/aceMode/s|,"yaml":"YAML"||' tinyfilemanager.php
    sed -i 's|"aceMode":{|&"yaml":"YAML",|' tinyfilemanager.php
    sudo mv -f tinyfilemanager.php /var/www/html/index.php
    wget -q geekfunklabs.com/gfl_logo.png
    sudo mv -f gfl_logo.png /var/www/html/
    ASK_TO_REBOOT=true
fi

if [[ $soundfonts == "yes" ]]; then
    inform "Downloading free soundfonts..."
	apt_pkg_install "unzip"
    apt_pkg_install "tap-plugins"
	apt_pkg_install "wah-plugins"
    wget -nv --show-progress geekfunklabs.com/squishbox_soundfonts.zip
    unzip -na squishbox_soundfonts.zip -d $installdir/SquishBox
    rm squishbox_soundfonts.zip
fi

success "Tasks complete!"

if $ASK_TO_REBOOT; then
    warning "\nSome changes made to your system require"
    warning "your computer to reboot to take effect."
    echo
    if promptoryes "Would you like to reboot now?"; then
        sync && sudo reboot
    fi
fi
