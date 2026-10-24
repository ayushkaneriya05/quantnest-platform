# Prepare a production server

Use this once for the Public host and again for a separate personal Private host.
Skip this document for local Development. These instructions use **Ubuntu 24.04
LTS**, matching the Python 3.12 host scripts. The applications run in Docker.

Provider dashboard labels can change. The linked official instructions are the
reference if a screen differs. This guide was checked on 24 October 2026.

## 1. Create the VM

You need a cloud account, an SSH key and a public address. Oracle is one option;
the Compose files do not depend on Oracle APIs or Terraform.

In your provider dashboard:

1. Create a Linux VM with Ubuntu 24.04 LTS, using either AMD64 or ARM64.
2. Choose CPU/RAM/disk capacity before confirming its cost. Current production
   Compose limits were prepared for a host with roughly 12 GiB RAM or more, with
   additional space needed for image builds and history. They are not a promise
   of a particular user count. Do not choose a 1 GiB VM for this full stack.
3. Use persistent storage with room for database growth, downloaded history,
   Docker images and temporary backup files. Watch free space after deployment.
4. Place the VM on a network that can reach the Internet. For the simple topology,
   it also needs inbound Internet access to HTTP/HTTPS.
5. Assign a stable/reserved public IP. Record the actual address and any charge.
6. Add your SSH public key, or download the private key if the provider generates
   the pair. Keep the private key on your own computer, outside the repository.
7. Record the server's username; the Ubuntu image normally uses `ubuntu`.

For Oracle, create a VCN with Internet connectivity, use its public subnet, and
check the Internet gateway/default route. Assign the VM's public IP and configure
its NSG/security list. Oracle explains the required network pieces in
[instance creation](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm)
and [public addresses](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm).
Free-tier eligibility, capacity and quotas must be checked in your own tenancy.

## 2. Set the network rules

Use stateful inbound TCP rules in the cloud firewall/security list:

| Destination port | Source | Purpose |
| --- | --- | --- |
| 22 | Your current public IP with `/32` | Your SSH terminal |
| 80 | Internet | Caddy HTTP redirect/certificate validation |
| 443 | Internet | Public origin or personal HTTPS site/WebSockets |

Allow outbound HTTPS/DNS and your configured SMTP connection. The simple stack
needs outbound access for package/image downloads, FYERS, NSE, Gemini and email.

Do not add inbound rules for 5432, 6379, 8000, 8001 or the execution buffers.
Production Compose publishes only Caddy's 80/443. Also check the host's firewall
if enabled. A cloud rule and a host rule are separate layers.

Docker-published ports can bypass ordinary UFW rules, so do not treat UFW alone
as a firewall for containers. See [Docker's firewall note](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations).
Keep the small published-port list in Compose and the cloud rules above.

## 3. Connect from Windows

Open **PowerShell on your own computer**, not the cloud browser console:

```powershell
ssh -i "$env:USERPROFILE\.ssh\quantnest-server.key" ubuntu@YOUR_SERVER_IP
```

Replace the key path and address. The key file must be the matching private key;
it is not the `.pub` file. Check the server fingerprint using the provider's
console before accepting a new host. After connection, the prompt should show
the Ubuntu server. All remaining commands in this document run there.

If SSH fails, check the username, key, public IP and port-22 source rule. If your
home public IP changes, update that rule. Do not solve it by publishing every port.

## 4. Install the small set of host tools

On a fresh Ubuntu host:

```sh
sudo apt update
sudo apt install -y git python3 python3-venv age curl ca-certificates dnsutils nano
python3 --version
```

Expected Python is 3.12 on Ubuntu 24.04. Git downloads source, age encrypts
backups, curl checks HTTP, dnsutils provides `dig`, and nano edits text files.
Python on the host runs the standard-library deployment helpers only.

Install Docker from its official Ubuntu repository:

```sh
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
```

This installs Engine, the CLI, Buildx and Compose from Docker's repository; the
last line grants your login access to the daemon. Docker access controls the host.
**Exit SSH and connect again** so group membership takes effect.
For a host with existing Docker packages, follow the official migration procedure
instead of mixing package sources. Reference: [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/).

After reconnecting:

```sh
docker version
docker compose version
docker run --rm hello-world
age --version
timedatectl status
df -h
free -h
```

Docker should show both Client and Server. Compose should be available; the
deployment uses its `--wait` option. The small hello-world container should finish
successfully. Confirm the clock is synchronized, disk has room, and RAM matches
the chosen VM. The application uses Asia/Kolkata for market sessions even if the
host displays UTC. A wrong clock affects OAuth, OTP and execution timestamps.

You do not need host Node, PostgreSQL, Redis, an application virtual environment,
Kubernetes, a separate process manager or OCI Python libraries for this procedure.

## 5. Give the server read access to your private repository

Use an existing approved Git authentication method if you already have one. For
a new GitHub repository deploy key, run on the server:

```sh
mkdir -p ~/.ssh
chmod 700 ~/.ssh
ssh-keygen -t ed25519 -f ~/.ssh/quantnest_deploy -C quantnest-server
cat ~/.ssh/quantnest_deploy.pub
```

Do not overwrite a key already at that path. Keep any chosen passphrase in your
password manager. Only the `.pub` output goes to GitHub. In your repository's
**Settings -> Deploy keys**, add it with read access. Leave write permission off.
Use [GitHub's deploy-key instructions](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys).

Then download the reviewed code:

```sh
GIT_SSH_COMMAND="ssh -i $HOME/.ssh/quantnest_deploy -o IdentitiesOnly=yes" git clone git@github.com:YOUR_ACCOUNT/YOUR_REPOSITORY.git QuantNest
cd QuantNest
git config core.sshCommand "ssh -i $HOME/.ssh/quantnest_deploy -o IdentitiesOnly=yes"
git status --short
git log -1 --oneline
```

Replace the repository path. The first command downloads it to `~/QuantNest`.
The config line makes later fetches use that same key. Check that the commit is
the intended release and contains `backend/execution`, the three Compose files,
and the shared Dockerfiles. If using another branch, select the reviewed branch
before configuring/deploying. Never clone over an existing deployment directory.

An empty `git status --short` means a fresh checkout; it does not mean external
integrations are configured. Your local uncommitted Windows files are not here.

## 6. Prepare DNS, then return to your mode guide

| Mode | DNS you need |
| --- | --- |
| Public | Browser domain attached to Pages; a separate DNS-only origin A record pointing at this VM |
| Private | Personal browser hostname A record pointing directly at this VM |

Create an AAAA record only if IPv6 actually reaches the same service. An incorrect
AAAA record can break browser access or certificate issuance even if IPv4 works.
Use `dig +short YOUR_HOSTNAME` to check resolution; do not enter `https://` in DNS.

Caddy issues ordinary HTTPS certificates when the configured hostname reaches
the host and its challenge traffic is reachable. There are no manual Origin CA
certificate files to copy. Its persistent certificate volume survives upgrades.
See [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https).

Continue at [Public setup](../public/SETUP.md) or [Private setup](../private/SETUP.md)
to create environment files. Leave the application stopped until its actual
configuration and secrets have been entered.
