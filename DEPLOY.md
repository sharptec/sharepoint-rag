# SharePoint RAG Application Deployment Guide

This guide explains how to host the SharePoint RAG application on a Linux VM (Ubuntu/Debian).

## Prerequisites
1. **Linux VM**: A server running Ubuntu 20.04/22.04 or Debian 11/12.
2. **Access**: SSH access to the VM.
3. **Ports**: Ensure port `8000` is open in your firewall (or Security Group if on AWS/Azure/GCP).

## Deployment Steps

### 1. Transfer Files to VM
You need to copy the project files to your VM. You can use `scp` (Secure Copy).

Run this command **from your local machine** (where the code is):

```bash
# Replace 'user' and 'your-vm-ip' with your actual VM details
scp -r /path/to/sharepoint_rag user@your-vm-ip:~/sharepoint_rag
```

### 2. Configure Environment Variables
On the VM, navigate to the uploaded folder and create your `.env` file.

```bash
cd ~/sharepoint_rag
cp .env.example .env
nano .env
```
Fill in your API keys (Google API Key, Microsoft Graph credentials).

### 3. Run the Setup Script
The `setup_vm.sh` script handles the installation of dependencies (Python, pip), setup of the virtual environment, and configuration of the Systemd service.

```bash
chmod +x deployment/setup_vm.sh
./deployment/setup_vm.sh
```

### 4. Verify Deployment
Once the script completes, the service should be running.

Check status:
```bash
sudo systemctl status sharepoint_rag
```

Check logs:
```bash
journalctl -u sharepoint_rag -f
```

### 5. Access the Application
Open your browser and navigate to:
`http://<YOUR_VM_IP>:8000`

## Troubleshooting

- **Service fails to start**: Check logs for missing environment variables.
  ```bash
  sudo journalctl -u sharepoint_rag -n 50
  ```
- **Permission errors**: Ensure the user has rights to write to logs (handled by Systemd usually, but check folder permissions).
- **Port unreachable**: Check firewall settings.
  ```bash
  sudo ufw status
  sudo ufw allow 8000
  ```
