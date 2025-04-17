import React, { useEffect, useRef } from 'react';
import Message from './Message';

function ChatWindow({ messages }) {
  const chatboxRef = useRef(null);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    if (chatboxRef.current) {
      chatboxRef.current.scrollTop = chatboxRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="chat-window" ref={chatboxRef}>
      {messages.map((msg) => (
        <Message key={msg.id} type={msg.type} text={msg.text} />
      ))}
    </div>
  );
}

export default ChatWindow;