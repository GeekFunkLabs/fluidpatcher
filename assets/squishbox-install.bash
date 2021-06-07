#!/bin/bash

installdir=""
logfile="install-log.txt"
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
			sudo apt-get -qqy upgrade --with-new-pkgs &>> $logfile
			sudo apt-get clean && sudo apt-get autoclean
			sudo apt-get -qqy autoremove
			UPGRADE=false
		fi
    fi
}

apt_pkg_install() {
    APT_CHK=$(dpkg-query -W -f='${Status}\n' "$1" 2> /dev/null | grep "install ok installed")
    if [[ $APT_CHK == "" ]]; then    
        echo "Apt is installing $1..."
        sudo apt-get --no-install-recommends --yes install "$1" &>> $logfile || { warning "Apt failed to install $1!" && exit 1; }
    fi
}

pip_install() {
    if [[ $PYTHON_PKG == "" ]]; then
        PYTHON_PKG=$(pip3 list 2> /dev/null)
    fi
    if ! [[ $PYTHON_PKG =~ "$1" ]]; then
        echo "Pip is installing $1..."
        sudo -H pip3 install "$1" &>> $logfile || { warning "Pip failed to install $1!" && exit 1; }
    fi
}


sleep 2
rm -f $logfile

## get options from the user

inform "\nThis script installs/updates software and optonal extras"
inform "for the SquishBox or headless Raspberry Pi synth."
warning "Always be careful when running scripts and commands copied"
warning "from the internet. Ensure they are from a trusted source."
echo "If you want to see what this script does before running it,"
echo "hit ctrl-C and enter 'curl https://geekfunklabs.com/squishbox | more'"
echo "Logging errors and technical output to $logfile"
echo -e "Report issues with this script at https://github.com/albedozero/fluidpatcher\n"

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

echo "Which audio output would you like to use?"
echo "  1. Add-on DAC (SquishBox)"
echo "  2. Headphone jack (headless pi)"
echo "  3. USB sound card"
echo "  0. No change"
query "Choose" "0"; audiosetup=$response

echo "What script should be run on startup?"
echo "  1. squishbox.py"
echo "  2. headlesspi.py"
echo "  3. Nothing"
echo "  0. No change"
query "Choose" "0"; startup=$response
if [[ $startup == 2 ]]; then
	echo -e "Set up controls for headless pi:"
	query "    MIDI channel for controls" "use default"; ctrls_channel=$response
	query "    Next patch button CC" "use default"; incpatch=$response
	query "    Previous patch button CC" "use default"; decpatch=$response
	query "    Patch select knob CC" "use default"; selectpatch=$response
	query "    Bank change button CC" "use default"; bankinc=$response
fi
if promptorno "OK to upgrade your system (if necessary)?"; then
	UPGRADE=true
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

umask 002 # friendly permissions for web file manager
if [[ $update == "yes" ]]; then
    inform "Installing/Updating FluidPatcher and any required packages..."
    # get dependencies
    sysupdate
    apt_pkg_install "git"
    apt_pkg_install "python3-pip"
    apt_pkg_install "python3-rtmidi"
    apt_pkg_install "libfluidsynth1"
    apt_pkg_install "fluid-soundfont-gm"
    pip_install "oyaml"
    pip_install "mido"
    pip_install "RPi.GPIO"
    pip_install "RPLCD"

    echo "Installing/Updating FluidPatcher version $NEW_FP_VER ..."
    rm -rf fluidpatcher
    git clone https://github.com/albedozero/fluidpatcher &>> $logfile
	cd fluidpatcher
    if [[ $overwrite == "yes" ]]; then
        find . -type d -exec mkdir -p $installdir/{} \; &>> ../$logfile
        find . -type f ! -name "hw_overlay.py" -exec cp -f {} $installdir/{} \; &>> ../$logfile
        find . -type f -name "hw_overlay.py" -exec cp -n {} $installdir/{} \; &>> ../$logfile
    else
        find . -type d -exec mkdir -p $installdir/{} \; &>> $logfile
        find . -type f ! -name "*.yaml" ! -name "hw_overlay.py" -exec cp -f {} $installdir/{} \; &>> ../$logfile
        find . -type f -name "hw_overlay.py" -exec cp -n {} $installdir/{} \; &>> ../$logfile
        find . -type f -name "*.yaml" -exec cp -n {} $installdir/{} \; &>> ../$logfile        
    fi
	cd ..
    rm -rf fluidpatcher
    ln -s /usr/share/sounds/sf2/FluidR3_GM.sf2 $installdir/SquishBox/sf2/ &>> $logfile
    
    # real-time audio tweaks
    sudo usermod -a -G audio pi
    AUDIOCONF="/etc/security/limits.d/audio.conf"
    if test -f "$AUDIOCONF"; then
        if ! grep -q "^@audio - rtprio 80" $AUDIOCONF; then
            echo "@audio - rtprio 80" | sudo tee -a $AUDIOCONF &>> $logfile
        fi
        if ! grep -q "^@audio - memlock unlimited" $AUDIOCONF; then
            echo "@audio - memlock unlimited" | sudo tee -a $AUDIOCONF &>> $logfile
        fi
    else
        echo -e "@audio - rtprio 80\n@audio - memlock unlimited" | sudo tee -a $AUDIOCONF &>> $logfile
    fi
fi

# set up audio
CONFIG="/boot/config.txt"
sudo mv /etc/xdg/autostart/piwiz.desktop /etc/xdg/autostart/piwiz.disabled &>> $logfile
if [[ $audiosetup =~ ^(1|2|3)$ ]]; then
	sudo sed -i "/dtparam=audio=on/d" $CONFIG
	sudo sed -i "/dtoverlay=hifiberry-dac/d" $CONFIG
fi
if [[ $audiosetup == "1" ]]; then
    echo "Activating DAC sound..."
	echo "dtoverlay=hifiberry-dac" | sudo tee -a $CONFIG &>> $logfile
    ASK_TO_REBOOT=true
elif [[ $audiosetup == "2" ]]; then
    echo "Activating headphone audio..."
	echo "dtparam=audio=on" | sudo tee -a $CONFIG &>> $logfile
    sudo amixer -q sset 'Headphone' 400
    ASK_TO_REBOOT=true
elif [[ $audiosetup == "3" ]]; then
    echo "Activating USB audio..."
	# nothing needed
    ASK_TO_REBOOT=true
fi

# set up services
if [[ $startup == "1" ]]; then
    echo "Enabling startup service..."
    chmod a+x $installdir/squishbox.py
    cat <<EOF | sudo tee /etc/systemd/system/squishbox.service &>> $logfile
[Unit]
Description=SquishBox
After=local-fs.target

[Service]
Type=simple
ExecStart=$installdir/squishbox.py
User=pi
WorkingDirectory=$installdir
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl enable squishbox.service &>> $logfile
    ASK_TO_REBOOT=true
elif [[ $startup == "2" ]]; then
    echo "Enabling startup service..."
    chmod a+x $installdir/headlesspi.py
    cat <<EOF | sudo tee /etc/systemd/system/squishbox.service &>> $logfile
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
    sudo systemctl enable squishbox.service &>> $logfile
	if ! [[ $decpatch == "use default" ]]; then
		sed -i "/^DEC_PATCH/s|[0-9]\+|$decpatch|" $installdir/headlesspi.py; fi
	if ! [[ $incpatch == "use default" ]]; then
		sed -i "/^INC_PATCH/s|[0-9]\+|$incpatch|" $installdir/headlesspi.py; fi
	if ! [[ $bankinc == "use default" ]]; then
		sed -i "/^BANK_INC/s|[0-9]\+|$bankinc|" $installdir/headlesspi.py; fi
	if ! [[ $selectpatch == "use default" ]]; then
		sed -i "/^SELECT_PATCH/s|[0-9]\+|$selectpatch|" $installdir/headlesspi.py; fi
	if ! [[ $ctrls_channel == "use default" ]]; then
		sed -i "/^CTRLS_MIDI_CHANNEL/s|[0-9]\+|$ctrls_channel|" $installdir/headlesspi.py; fi
    ASK_TO_REBOOT=true
elif [[ $startup == "3" ]]; then
    echo "Disabling startup service..."
    sudo systemctl disable squishbox.service &>> $logfile
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
    sudo apt-get build-dep fluidsynth --no-install-recommends --yes &>> $logfile
    rm -rf fluidsynth
    git clone https://github.com/FluidSynth/fluidsynth &>> $logfile
    mkdir fluidsynth/build
    cd fluidsynth/build
    echo "Configuring..."
    cmake .. &>> $logfile
    echo "Compiling..."
    make &>> $logfile
    sudo make install &>> $logfile
    sudo ldconfig &>> $logfile
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
    cat <<'EOF' | sudo tee /etc/nginx/sites-available/default &>> $logfile
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
    echo "Configuring file manager..."
    wget -q raw.githubusercontent.com/prasathmani/tinyfilemanager/master/tinyfilemanager.php
    sudo sed -i "/define('APP_TITLE'/cdefine('APP_TITLE', 'SquishBox Manager');" tinyfilemanager.php
    sudo sed -i "/'admin' =>/d;/'user' =>/d" tinyfilemanager.php
    sudo sed -i "/\$auth_users =/a    '$fmgr_user' => '$fmgr_hash'" tinyfilemanager.php
    sudo sed -i "/\$theme =/c\$theme = 'dark';" tinyfilemanager.php
    sudo sed -i "0,/root_path =/s|root_path = .*|root_path = '$installdir/SquishBox';|" tinyfilemanager.php
    sudo sed -i "0,/favicon_path =/s|favicon_path = .*|favicon_path = 'gfl_logo.png';|" tinyfilemanager.php
    sudo sed -i '/aceMode/s|,"yaml":"YAML"||' tinyfilemanager.php
    sudo sed -i 's|"aceMode":{|&"yaml":"YAML",|' tinyfilemanager.php
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
    unzip -na squishbox_sfpack.zip -d $installdir/SquishBox
    rm squishbox_sfpack.zip
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
