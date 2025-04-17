import React, { useState, useCallback } from 'react';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
// Removed App.css import here as it's imported in main.jsx

function App() {
  // Initial welcome message
  const initialMessages = [
      { id: Date.now(), type: 'assistant', text: 'Hello! How can I assist you today?' }
  ];
  const [messages, setMessages] = useState(initialMessages);
  const [isLoading, setIsLoading] = useState(false);
  // We might display errors directly in the chat now
  // const [error, setError] = useState(null);

  const handleSendMessage = useCallback(async (inputText) => {
    if (!inputText || isLoading) return; // Prevent sending empty or while loading

    const timestamp = Date.now(); // Simple unique ID for keys
    const userMessage = { id: timestamp, type: 'user', text: inputText };
    setMessages(prev => [...prev, userMessage]); // Add user message immediately
    setIsLoading(true);
    // setError(null); // Clear previous errors if needed

    // Add a temporary loading message
    const loadingId = timestamp + 1;
    const loadingMessage = { id: loadingId, type: 'loading', text: 'Assistant is thinking...' };
    setMessages(prev => [...prev, loadingMessage]);


    try {
      // Fetch uses the relative path, Vite proxy handles forwarding in dev
      const response = await fetch('/api/chat', { // Path matches api_server.py endpoint
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: inputText }), // Ensure key matches backend ("query")
      });

      const data = await response.json();

      // Remove the loading message before adding the real response or error
      setMessages(prev => prev.filter(msg => msg.id !== loadingId));


      if (!response.ok || data.error) {
        throw new Error(data.error || `HTTP error ${response.status}`);
      }

      const assistantMessage = { id: Date.now(), type: 'assistant', text: data.response };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (err) {
       // Remove the loading message if an error occurred
      setMessages(prev => prev.filter(msg => msg.id !== loadingId));

      console.error("API Error:", err);
      // setError(err.message || "Failed to get response from assistant.");
      // Add an error message to the chat window
      const errorMessage = { id: Date.now(), type: 'error', text: `Error: ${err.message || "Failed to get response."}` };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]); // Dependency array for useCallback

  return (
    <div className="app-container">
      <ChatWindow messages={messages} />
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </div>
  );
}

export default App;