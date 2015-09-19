# -*- mode: ruby -*-
# vi: set ft=ruby :
Vagrant.require_version ">= 1.7.2"
VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
	config.vm.box = 'ubuntu/vivid64'
	config.vm.provision :shell, path: "vagrant/bootstrap.sh", privileged: false

	# Compilation of lxml requires a little bit more memory than
	# default 512 megabytes.
	config.vm.provider :virtualbox do |provider|
		provider.memory = 1024
		provider.gui = true
	end

	# Networking settings
	config.ssh.forward_agent = true
	config.vm.network "forwarded_port", guest: 8000, host: 8000
end