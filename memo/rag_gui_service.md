### Memo: Steps for Deploying and Managing Streamlit App with Supervisor on Ubuntu
Jan 06 2025

This memo outlines the steps followed to deploy and manage a Streamlit app using **Supervisor** on an **Ubuntu** server. It includes instructions for starting, debugging, and restarting the app in the future.

---

### **1. Set up the Ubuntu Environment**
Ensure the necessary dependencies are installed:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx supervisor
```

### **2. Set up Python Virtual Environment**
Create a Python virtual environment and activate it:

```bash
cd /root  # Navigate to your desired directory
python3 -m venv venv  # Create virtual environment
source venv/bin/activate  # Activate virtual environment
```

### **3. Install Dependencies**
Install the necessary Python dependencies inside the virtual environment:

```bash
pip install streamlit
pip install -r /root/legal_qa_rag/requirements.txt  # Install other dependencies
```

### **4. Create Supervisor Configuration for Streamlit**
Create and configure the Supervisor process to run the Streamlit app. The Supervisor configuration file is located in `/etc/supervisor/conf.d/`:

1. **Create a Supervisor configuration file** (`rag-gui.conf`):

   ```bash
   sudo nano /etc/supervisor/conf.d/rag-gui.conf
   ```

2. **Supervisor configuration content**:

   ```ini
   [program:rag-gui]
   command=/root/venv/bin/streamlit run /root/legal_qa_rag/rag_service/src/rag_gui.py
   directory=/root/legal_qa_rag
   autostart=true
   autorestart=true
   stderr_logfile=/var/log/streamlitapp.err.log
   stdout_logfile=/var/log/streamlitapp.out.log
   user=root
   environment=PATH="/root/venv/bin:/usr/bin",VIRTUAL_ENV="/root/venv"
   ```

3. **Explanation of directives**:
   - `command`: Full path to the `streamlit` executable within the virtual environment.
   - `directory`: Set to `/root/legal_qa_rag` (absolute path to the project).
   - `stderr_logfile` and `stdout_logfile`: Logs for error and output capture.
   - `user`: Running as `root` (or another user if desired).
   - `environment`: Environment variables like `VIRTUAL_ENV` and `PATH` to point to the virtual environment.

### **5. Reload and Start Streamlit App with Supervisor**
After creating the configuration file, you can reload Supervisor to read the configuration and start the process:

```bash
sudo supervisorctl reread  # Detect new configuration
sudo supervisorctl update  # Apply changes
sudo supervisorctl start rag-gui  # Start the Streamlit app
```

### **6. Debugging the App**
If the app fails to start, check the Supervisor logs and the app logs for error messages:

```bash
# Supervisor logs
sudo tail -f /var/log/supervisor/supervisord.log

# App-specific error logs
sudo tail -f /var/log/streamlitapp.err.log
sudo tail -f /var/log/streamlitapp.out.log
```

**Common Issues:**
- **ENOENT (Directory not found)**: Make sure the `directory` path in the Supervisor config points to the correct absolute path.
- **Invalid file path**: Ensure the file paths in the Supervisor config are correct (`/root/legal_qa_rag/rag_service/src/rag_gui.py`).

### **7. Manually Testing the Command**
Before using Supervisor, you can test the `streamlit` command manually:

```bash
/root/venv/bin/streamlit run /root/legal_qa_rag/rag_service/src/rag_gui.py
```

If this works, Supervisor should work as well.

### **8. Restarting the App**
To restart the app via Supervisor, use:

```bash
sudo supervisorctl restart rag-gui
```

### **9. Updating the App**
If you need to update the app or its dependencies:
1. Pull the latest changes from GitHub (if applicable).
2. Install any new dependencies:
   ```bash
   pip install -r /root/legal_qa_rag/requirements.txt
   ```
3. Restart the app:
   ```bash
   sudo supervisorctl restart rag-gui
   ```

### **10. Managing Logs**
To check the logs for any issues with the Streamlit app, use:

```bash
sudo tail -f /var/log/streamlitapp.err.log  # For error logs
sudo tail -f /var/log/streamlitapp.out.log  # For output logs
```

### **11. Troubleshooting Tips**
- If Supervisor logs indicate a file or directory issue (like `ENOENT`), double-check the file paths in the Supervisor configuration.
- Verify permissions on directories and files to ensure that the process has access.

### **12. Stopping the App**
To stop the Streamlit app, use:

```bash
sudo supervisorctl stop rag-gui
```

---

By following these steps, you can deploy, restart, and debug your Streamlit app easily on the Ubuntu server using Supervisor. If you need to make any adjustments, just update the Supervisor configuration file and reload the configuration.

Let me know if you need further assistance!