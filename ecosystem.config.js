module.exports = {
    apps: [
      {
        name: 'personal-assistant',
        script: 'python',
        args: 'main.py --api-host 0.0.0.0 --api-port 8081 --mcp-host 0.0.0.0 --mcp-port 9091',
        interpreter: 'python3',  // Adjust if you use a different interpreter
        autorestart: true,
        watch: false,
        max_memory_restart: '512M'
      }
    ]
  };
  