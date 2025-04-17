// MCP_Agents/ecosystem.config.js
/**
 * PM2 Configuration File
 *
 * Defines how to run the MCP Agents application using PM2.
 * It specifies the script, interpreter, arguments, and process management settings.
 */
module.exports = {
  apps: [
    {
      name: 'mcp-agent', // Application name shown in PM2
      script: 'main.py', // The main script to execute
      interpreter: 'python3', // Or specify the path to your virtualenv python

      // Arguments passed to main.py.
      // Host/port args are optional here if main.py reads them from .env or defaults.
      // Only include args if you need to OVERRIDE the .env/defaults via PM2.
      // Example:
      // args: '--api-port 8082 --mcp-port 9092',
      args: '', // Let main.py use .env or its defaults

      // --- Process Management ---
      instances: 1, // Number of instances to run (usually 1 unless load balancing)
      autorestart: true, // Automatically restart if the app crashes
      watch: false, // Set to true to restart on file changes (useful for dev, disable for prod)
      // watch_options: { // Fine-tune watch behavior if enabled
      //   "followSymlinks": false,
      //   "usePolling": true, // Needed in some environments (like Docker)
      //   "interval": 500 // Poll interval
      // },
      max_memory_restart: '512M', // Restart if memory usage exceeds this limit

      // --- Logging (PM2 handles merging logs) ---
      // PM2 captures stdout/stderr. Define log file paths if needed.
      // output: './logs/pm2-out.log', // PM2 stdout log
      // error: './logs/pm2-err.log',  // PM2 stderr log
      // log_date_format: 'YYYY-MM-DD HH:mm:ss Z', // Optional log date format

      // --- Environment Variables (Optional) ---
      // You can inject environment variables here, but using .env is generally preferred
      // env: {
      //   NODE_ENV: 'development',
      // },
      // env_production: {
      //   NODE_ENV: 'production',
      // }
    }
  ]
};