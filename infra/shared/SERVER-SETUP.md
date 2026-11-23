# Prepare an Oracle Cloud production server

Use this once for the Public host and again for each separate managed Private
host. A personal Private instance uses the same setup. Keep customer databases,
credentials, volumes and backups isolated; the initial flow is one stack per host.
Skip this document for local Development. These instructions use **Ubuntu 24.04
LTS**, matching the Python 3.12 host scripts. The applications run in Docker.

Oracle dashboard labels and entitlements can change. Console steps and the
official references below were checked on **18 November 2026**. The application
does not need Oracle SDKs, Terraform, a load balancer or Kubernetes. The same Linux
procedure works on another provider, with its own network/IP configuration.

## 1. Create the Oracle VM

### Account, region and capacity

Sign into the OCI Console, protect the operator account with MFA, select your
intended region and create/select a compartment such as `quantnest-public` or
`quantnest-private`. A compartment groups resources; it does not run software.
Use the tenancy's home region when claiming Always Free resources.

| Choice | Meaning for this repository |
| --- | --- |
| `VM.Standard.A1.Flex` | ARM64 Ampere host; choose an ARM64-compatible Ubuntu image and build native application images on it |
| AMD/Intel VM | AMD64 host; usable with the same Compose files when adequately sized, but not necessarily free |
| `VM.Standard.E2.1.Micro` | 1 GB RAM; unsuitable for this complete application stack |
| Initial sizing | Approximately 12 GB RAM, `API_WORKERS=1`, `EXECUTION_WORKERS=1`; measure before increasing concurrency |
| Storage | Persistent boot volume with space for Docker, confirmed candle history, database growth and backup temporary files |

Oracle currently documents **2 A1 OCPUs / 12 GB total** for Always Free tenancies,
with 1,500 OCPU-hours and 9,000 GB-hours monthly. Its 200 GB boot/block storage
allowance is shared. Check your tenancy's actual entitlement/cost before creation;
do not assume the older 4-OCPU/24-GB offer. Capacity shortages and idle-instance
reclamation are possible. See [Oracle Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

Public and Private need separate hosts/databases. Two full 12-GB deployments do
not fit that single free A1 allocation. Choose which to start or budget separately;
do not split it into undersized production VMs or assume a free allocation per VM.
An OCI [budget alert](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/budgetsoverview.htm)
notifies about spending; it is not a hard spending cap.

### Console creation sequence

1. Open **Networking → Virtual Cloud Networks** in the selected compartment.
   Create a VCN with a **public subnet**, Internet Gateway and a subnet route
   `0.0.0.0/0 → Internet Gateway`. If using a wizard, inspect its proposed resources;
   this single-public-host layout needs no NAT Gateway or load balancer.
2. Create a Network Security Group, e.g. `quantnest-web`, and add the rules in
   Step 2. Check the subnet's Security Lists too; NSG rules do not override a
   broader allow rule already in a Security List.
3. Open **Compute → Instances → Create instance**. Use a clear mode-specific name,
   the selected compartment and **Canonical Ubuntu 24.04 LTS**. Match image and
   shape architecture. These `apt` instructions are not for Oracle Linux.
4. Select shape/CPU/RAM and review its estimated charge. Prefer a boot volume
   around 100 GB if it fits your remaining storage allowance; larger history
   datasets need a deliberate capacity plan. Avoid accidental volume deletion
   on termination. New disks/partitions must actually be mounted before use.
5. Select the public subnet, attach `quantnest-web`, and enable a public IPv4
   address on the primary VNIC. An Internet Gateway alone does not assign an IP.
6. Upload your SSH **public** key, or securely save the private key if OCI
   generates the pair. Keep private keys on your operator computer, outside Git.
   Record the Ubuntu login name, normally `ubuntu`.
7. Create the instance. Record region, compartment, instance/VNIC, boot volume,
   image architecture and public IPv4. Wait for the instance to run.

See [Oracle instance creation](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm)
and [Internet/public-IP requirements](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm).

### Keep the address stable

Before setting DNS or broker IP access, choose an OCI **Reserved Public IP** and
associate it with the VNIC's primary private IP. The Console exposes this through
the instance's attached VNIC/IP details and Networking's Public IP management.
Replacing an already assigned ephemeral address changes the public IP: record
the new address and use it for SSH/DNS/provider configuration.

The existing ephemeral address cannot be converted into an identical reserved
address. A reserved address can be reassigned within its region during recovery.
Do not perform that reassignment on a running trading host as a routine setup
step. Reconnect SSH using the new address before continuing. See
[Oracle public-IP types and management](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm).

## 2. Set the network rules

In `quantnest-web`, create **stateful ingress** rules. Set the TCP **destination**
port; leave source ports unrestricted:

| Destination port | Source | Purpose |
| --- | --- | --- |
| 22 | Your current public IP with `/32` | Your SSH terminal |
| 80 | `0.0.0.0/0` | Caddy HTTP redirect/certificate validation |
| 443 | `0.0.0.0/0` | Public origin or personal HTTPS site/WebSockets |

Replace the port-22 source with your administration computer's actual public
IPv4 plus `/32`. Attach the NSG to the instance's VNIC. Remove an unnecessary
default `0.0.0.0/0` SSH allow from the subnet Security List after preserving your
working SSH access. Preserve required Oracle instance-service/ICMP rules. Rules
across applicable NSGs and Security Lists are combined as allows, not as a
restrictive intersection. See [Oracle security rules](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securityrules.htm).

Keep the normal outbound Internet rule for this initial simple deployment. It
supports package/image downloads, provider HTTPS/WebSockets, DNS, time sync and
SMTP on 587. If restricting egress later, account for HTTP/HTTPS, DNS, NTP and
your SMTP endpoint plus OCI instance/storage services. This layout uses an
Internet Gateway/public IP for egress, not a NAT Gateway.

Do not add inbound rules for 5432, 6379, 8000, 8001 or the execution buffers.
Production Compose publishes only Caddy's 80/443. Also check the host's firewall
if enabled. A cloud rule and a host rule are separate layers.

Docker-published ports can bypass ordinary UFW rules, so do not treat UFW alone
as a firewall for containers. See [Docker's firewall note](https://docs.docker.com/engine/install/ubuntu/#firewall-limitations).
Keep the small published-port list in Compose and the cloud rules above.

Do not restrict Public origin ingress to only Cloudflare proxy ranges: this
repository's Pages Function and DNS-only origin layout also needs Caddy's public
certificate challenges. Keep the application gateway-token check in place.

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

### Oracle Ubuntu host firewall, before Docker installation

Oracle's Ubuntu images can retain iptables rejection rules even when no UFW
service is active. OCI ingress rules and the guest firewall are separate layers.
Inspect the existing rules rather than flushing them:

```sh
sudo iptables -S INPUT
sudo iptables -S FORWARD
sudo ls /etc/iptables
```

On the fresh Oracle Ubuntu image using its existing `netfilter-persistent`,
allow only the web ports and save **before installing Docker**:

```sh
sudo iptables -C INPUT -p tcp -m multiport --dports 80,443 -j ACCEPT || sudo iptables -I INPUT 1 -p tcp -m multiport --dports 80,443 -j ACCEPT
sudo netfilter-persistent save
```

`-C` checks for the exact rule; `-I` adds it if absent, ahead of a final rejection.
Saving now retains the host rules without persisting Docker's later dynamic
chains. On a host where Docker already runs, manage the persistent host rule in
`/etc/iptables/rules.v4` and inspect Docker's FORWARD/DOCKER-USER chains separately;
do not flush/reload all rules or save stale container chains as a generic fix.
Keep the current SSH connection open and verify a second connection after edits.

Do not install UFW on Oracle Ubuntu 24.04 as a shortcut: Canonical documents a
conflict with Oracle's persistent rules and storage-related configuration. Follow
[Canonical's Oracle image notes](https://documentation.ubuntu.com/release-notes/24.04/)
and [Oracle's Ubuntu firewall example](https://docs.oracle.com/en-us/iaas/Content/developer/apache-on-ubuntu/01oci-ubuntu-apache-summary.htm).

## 4. Install the small set of host tools

On a fresh Ubuntu host:

```sh
sudo apt update
sudo apt install -y git python3 python3-venv age curl ca-certificates dnsutils nano
python3 --version
uname -m
dpkg --print-architecture
lsblk -f
```

Expected Python is 3.12 on Ubuntu 24.04. Git downloads source, age encrypts
backups, curl checks HTTP, dnsutils provides `dig`, and nano edits text files.
Python on the host runs the standard-library deployment helpers only.
`aarch64`/`arm64` identifies A1; `x86_64`/`amd64` identifies an x86 host. Check the
clock and install available OS security updates while the new host is empty;
complete a required reboot before deploying the application.

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

### Native ARM images on Ampere A1

The currently referenced Timescale digest and Redis/Python/Node/Caddy image tags
were checked against Docker Registry manifests on 18 November 2026: each includes
Linux ARM64 and AMD64. This checks base-image availability, not every Python wheel
or a complete A1 deployment. Do the final locked build and application acceptance
on your chosen architecture. Do not force `platform: linux/amd64` on A1.

Build the backend/research and Private frontend **on the server**, using the mode
guide. An AMD64 image exported from your Windows laptop is not a native A1 image.
The Public frontend is built by Cloudflare Pages, so it needs no host Node.

If pulling/building fails, check DNS, outbound access, time and any configured
Docker registry mirror. A mirror TLS timeout is not a Django migration error.
Do not disable TLS verification or install packages into an existing running API
container as a workaround. Inspect Docker settings without publishing secrets.

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

For personal broker IP registration, use this host's stable **outbound** public
address, not the VCN's private address, Docker bridge address or Cloudflare IP.
This topology normally uses the reserved primary public IP for outbound traffic;
verify the address your broker actually sees, particularly after recovery.

Continue at [Public setup](../public/SETUP.md) or [Private setup](../private/SETUP.md)
to create environment files and deploy. Leave the application stopped until its
actual configuration and secrets have been entered. Step 7 below is for checks
after that deployment and later maintenance.

## 7. Verify access and keep the host maintainable

After the mode deployment starts Caddy, test from your **Windows computer**:

```powershell
Test-NetConnection YOUR_SERVER_IP -Port 22
Test-NetConnection YOUR_SERVER_IP -Port 80
Test-NetConnection YOUR_SERVER_IP -Port 443
```

Then test the hostname with `curl -I https://YOUR_HOSTNAME` and inspect Caddy logs.
For Public, the browser uses Pages and a direct origin health request without the
gateway token deliberately returns 403. For Private, `/health/` should return
Private mode once its dependencies are ready. Do not expect HTTP service before
the relevant mode has configured and started its ingress container.

| Symptom | Check first |
| --- | --- |
| SSH times out | Correct public IP/VNIC, subnet route, NSG attachment, Security Lists and your `/32` source |
| SSH permission denied | `ubuntu` username and matching private key; not the `.pub` file |
| 80/443 time out | OCI rules, guest firewall/Docker forwarding, then whether ingress is running |
| HTTPS certificate error | DNS A/AAAA, Internet reachability of challenges, correct hostname and synchronized clock |
| `no matching manifest` / `exec format error` | Image platform versus host architecture; rebuild natively |
| Docker mirror TLS timeout | Registry connectivity/mirror configuration; preserve certificate verification |
| Database fills disk | `df -h`, Docker usage, candle growth and temporary backups; expand deliberately, never prune application volumes |

Docker keeps its data under its configured data root; with the default setup this
is on the boot filesystem. Enlarging a cloud volume alone does not prove the guest
partition/filesystem grew: verify `lsblk -f` and `df -h`, then follow
[Oracle volume resizing](https://docs.oracle.com/en-us/iaas/Content/Block/Tasks/resizingavolume.htm)
for that layout. Retain a backup before storage changes.

Back up application data off-host with [Recovery setup](RECOVERY-SETUP.md).
Preserve the boot volume when replacing a VM until recovery has been proved.
Cloud snapshots can supplement the stopped application backup; they do not
replace its database/media/credential-key recovery procedure.
