#!/usr/bin/env python3
"""FastAPI web application to monitor Meshtastic messages in real-time."""

import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from contextlib import asynccontextmanager

# Database configuration
DB_PATH = os.getenv("DB_PATH", "meshtastic_messages.db")

# Store active WebSocket connections
active_connections: List[WebSocket] = []


class MessageMonitor:
    """Monitor database for new messages."""
    
    def __init__(self):
        self.last_id = 0
        self.running = False
    
    async def start(self):
        """Start monitoring for new messages."""
        self.running = True
        # Get the latest message ID
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(id) FROM messages")
        result = cursor.fetchone()
        self.last_id = result[0] if result[0] else 0
        conn.close()
        
        # Start monitoring loop
        asyncio.create_task(self.monitor_loop())
    
    async def stop(self):
        """Stop monitoring."""
        self.running = False
    
    async def monitor_loop(self):
        """Continuously check for new messages."""
        while self.running:
            try:
                new_messages = self.get_new_messages()
                if new_messages:
                    # Broadcast new messages to all connected clients
                    for message in new_messages:
                        await self.broadcast_message(message)
                        self.last_id = message['id']
                
                await asyncio.sleep(0.5)  # Check every 500ms
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                await asyncio.sleep(1)
    
    def get_new_messages(self):
        """Get messages newer than last_id."""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, timestamp, channel_index, channel_name, 
                       from_id, from_name, to_id, message_text, created_at
                FROM messages 
                WHERE id > ?
                ORDER BY id ASC
            """, (self.last_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'channel_index': row['channel_index'],
                    'channel_name': row['channel_name'],
                    'from_id': hex(row['from_id']),
                    'from_name': row['from_name'],
                    'to_id': hex(row['to_id']),
                    'message_text': row['message_text'],
                    'created_at': row['created_at']
                })
            
            conn.close()
            return messages
        except Exception as e:
            print(f"Error getting new messages: {e}")
            return []
    
    async def broadcast_message(self, message):
        """Send message to all connected WebSocket clients."""
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            if connection in active_connections:
                active_connections.remove(connection)


# Message monitor instance
monitor = MessageMonitor()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    await monitor.start()
    print("Message monitor started")
    yield
    # Shutdown
    await monitor.stop()
    print("Message monitor stopped")


# Create FastAPI app
app = FastAPI(title="Meshtastic Message Monitor", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main HTML page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meshtastic Message Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 30px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            margin-bottom: 30px;
        }
        
        h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #666;
            font-size: 0.9em;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .filters {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 20px;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .filter-group {
            flex: 1;
            min-width: 200px;
        }
        
        .filter-group label {
            display: block;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        .filter-group select {
            width: 100%;
            padding: 10px 15px;
            border: 2px solid #e5e7eb;
            border-radius: 10px;
            font-size: 1em;
            transition: all 0.3s;
            background: white;
        }
        
        .filter-group select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .messages-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            padding: 30px;
            max-height: 70vh;
            overflow-y: auto;
        }
        
        .messages-container::-webkit-scrollbar {
            width: 10px;
        }
        
        .messages-container::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        .messages-container::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }
        
        .message {
            background: white;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message:hover {
            box-shadow: 0 6px 25px rgba(0, 0, 0, 0.15);
            transform: translateY(-2px);
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .message-sender {
            font-weight: bold;
            color: #333;
            font-size: 1.1em;
        }
        
        .message-channel {
            display: inline-block;
            padding: 5px 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .message-time {
            color: #999;
            font-size: 0.85em;
        }
        
        .message-text {
            color: #555;
            line-height: 1.6;
            font-size: 1em;
            margin-top: 10px;
            word-wrap: break-word;
        }
        
        .no-messages {
            text-align: center;
            color: #999;
            padding: 40px;
            font-size: 1.1em;
        }
        
        .channel-primary { border-left-color: #3b82f6; }
        .channel-michigan { border-left-color: #10b981; }
        .channel-sumat { border-left-color: #f59e0b; }
        .channel-farmington { border-left-color: #ef4444; }
        .channel-wmi { border-left-color: #8b5cf6; }
        .channel-emi { border-left-color: #ec4899; }
        .channel-muskegon { border-left-color: #06b6d4; }
        .channel-umichmesh { border-left-color: #84cc16; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>
                📡 Meshtastic Message Monitor
            </h1>
            <div class="status">
                <div class="status-dot"></div>
                <span id="connection-status">Connected</span>
            </div>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value" id="total-messages">0</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="active-channels">0</div>
                    <div class="stat-label">Active Channels</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="active-nodes">0</div>
                    <div class="stat-label">Active Nodes</div>
                </div>
            </div>
        </header>
        
        <div class="filters">
            <div class="filter-group">
                <label for="channel-filter">Filter by Channel</label>
                <select id="channel-filter">
                    <option value="">All Channels</option>
                </select>
            </div>
            <div class="filter-group">
                <label for="node-filter">Filter by Node</label>
                <select id="node-filter">
                    <option value="">All Nodes</option>
                </select>
            </div>
        </div>
        
        <div class="messages-container" id="messages">
            <div class="no-messages">Waiting for messages...</div>
        </div>
    </div>
    
    <script>
        let ws;
        let messages = [];
        let channels = new Set();
        let nodes = new Set();
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
            
            ws.onopen = () => {
                document.getElementById('connection-status').textContent = 'Connected';
                loadRecentMessages();
            };
            
            ws.onclose = () => {
                document.getElementById('connection-status').textContent = 'Disconnected - Reconnecting...';
                setTimeout(connect, 2000);
            };
            
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                addMessage(message);
            };
        }
        
        async function loadRecentMessages() {
            try {
                const response = await fetch('/api/messages?limit=50');
                const data = await response.json();
                messages = data.reverse();
                messages.forEach(msg => {
                    channels.add(msg.channel_name);
                    nodes.add(msg.from_name);
                });
                updateFilters();
                renderMessages();
                updateStats();
            } catch (error) {
                console.error('Error loading messages:', error);
            }
        }
        
        function addMessage(message) {
            messages.unshift(message);
            channels.add(message.channel_name);
            nodes.add(message.from_name);
            
            // Keep only last 100 messages in memory
            if (messages.length > 100) {
                messages.pop();
            }
            
            updateFilters();
            renderMessages();
            updateStats();
        }
        
        function updateFilters() {
            const channelFilter = document.getElementById('channel-filter');
            const nodeFilter = document.getElementById('node-filter');
            
            const currentChannel = channelFilter.value;
            const currentNode = nodeFilter.value;
            
            channelFilter.innerHTML = '<option value="">All Channels</option>';
            Array.from(channels).sort().forEach(channel => {
                const option = document.createElement('option');
                option.value = channel;
                option.textContent = channel;
                if (channel === currentChannel) option.selected = true;
                channelFilter.appendChild(option);
            });
            
            nodeFilter.innerHTML = '<option value="">All Nodes</option>';
            Array.from(nodes).sort().forEach(node => {
                const option = document.createElement('option');
                option.value = node;
                option.textContent = node;
                if (node === currentNode) option.selected = true;
                nodeFilter.appendChild(option);
            });
        }
        
        function renderMessages() {
            const container = document.getElementById('messages');
            const channelFilter = document.getElementById('channel-filter').value;
            const nodeFilter = document.getElementById('node-filter').value;
            
            let filtered = messages;
            if (channelFilter) {
                filtered = filtered.filter(m => m.channel_name === channelFilter);
            }
            if (nodeFilter) {
                filtered = filtered.filter(m => m.from_name === nodeFilter);
            }
            
            if (filtered.length === 0) {
                container.innerHTML = '<div class="no-messages">No messages found</div>';
                return;
            }
            
            container.innerHTML = filtered.map(msg => {
                const time = new Date(msg.timestamp);
                const channelClass = `channel-${msg.channel_name.toLowerCase().replace(/\s+/g, '-')}`;
                
                return `
                    <div class="message ${channelClass}">
                        <div class="message-header">
                            <div>
                                <span class="message-sender">${escapeHtml(msg.from_name)}</span>
                                <span class="message-channel">${escapeHtml(msg.channel_name)}</span>
                            </div>
                            <div class="message-time">${formatTime(time)}</div>
                        </div>
                        <div class="message-text">${escapeHtml(msg.message_text)}</div>
                    </div>
                `;
            }).join('');
        }
        
        function updateStats() {
            document.getElementById('total-messages').textContent = messages.length;
            document.getElementById('active-channels').textContent = channels.size;
            document.getElementById('active-nodes').textContent = nodes.size;
        }
        
        function formatTime(date) {
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        document.getElementById('channel-filter').addEventListener('change', renderMessages);
        document.getElementById('node-filter').addEventListener('change', renderMessages);
        
        connect();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/messages")
async def get_messages(limit: int = 50, channel: Optional[str] = None):
    """Get recent messages from the database."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = """
            SELECT id, timestamp, channel_index, channel_name, 
                   from_id, from_name, to_id, message_text, created_at
            FROM messages 
        """
        params = []
        
        if channel:
            query += " WHERE channel_name = ?"
            params.append(channel)
        
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'channel_index': row['channel_index'],
                'channel_name': row['channel_name'],
                'from_id': hex(row['from_id']),
                'from_name': row['from_name'],
                'to_id': hex(row['to_id']),
                'message_text': row['message_text'],
                'created_at': row['created_at']
            })
        
        conn.close()
        return messages
    except Exception as e:
        return {"error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time message updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)
