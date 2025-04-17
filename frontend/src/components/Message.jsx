import React from 'react';

function Message({ type, text }) {
  // Add specific styling or icons based on type if needed
  return (
    <div className={`message ${type}`}>
      {text}
    </div>
  );
}

export default Message;