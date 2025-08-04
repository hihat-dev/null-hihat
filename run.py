#!/usr/bin/env python3
"""
Remote Desktop Server
Compatible with the provided Python client
"""

import os
import sys
from server import app, socketio

def main():
    print("=" * 60)
    print("🚀 REMOTE DESKTOP SERVER")
    print("=" * 60)
    print()
    print("📡 Server Configuration:")
    print(f"   • Host: 0.0.0.0")
    print(f"   • Port: 5000")
    print(f"   • Web Interface: http://localhost:5000")
    print(f"   • WebSocket: ws://localhost:5000")
    print()
    print("🔗 Client Connection:")
    print("   Update your client to connect to:")
    print("   url = 'localhost:5000'")
    print("   https = False")
    print()
    print("📋 Features:")
    print("   ✅ Real-time screen streaming")
    print("   ✅ Remote desktop control")
    print("   ✅ File explorer")
    print("   ✅ Terminal access")
    print("   ✅ File upload/download")
    print("   ✅ Multi-client support")
    print()
    print("🌐 Open http://localhost:5000 in your browser")
    print("=" * 60)
    print()
    
    try:
        port = int(os.environ.get("PORT", 10000))
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
