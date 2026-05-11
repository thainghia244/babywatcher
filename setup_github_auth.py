#!/usr/bin/env python3
"""
GitHub Authentication Setup Script for BabyWatcher
"""

import subprocess
import sys
import getpass

def setup_github_auth():
    """Setup GitHub authentication with Personal Access Token"""

    print("🔐 GitHub Authentication Setup for thainghia244")
    print("=" * 50)

    print("\n📋 Steps to get Personal Access Token:")
    print("1. Go to: https://github.com/settings/tokens")
    print("2. Click 'Generate new token (classic)'")
    print("3. Select scopes: 'repo' (full control of private repositories)")
    print("4. Copy the generated token")

    token = getpass.getpass("\n🔑 Enter your GitHub Personal Access Token: ").strip()

    if not token:
        print("❌ No token provided. Exiting...")
        return False

    try:
        # Configure credential helper
        subprocess.run(["git", "config", "--global", "credential.helper", "store"],
                      check=True, capture_output=True)

        # Test authentication by attempting to push
        print("\n🔄 Testing authentication...")

        # First, try to fetch to test credentials
        result = subprocess.run(["git", "fetch", "origin"],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Authentication successful!")
            print("🚀 You can now push your changes:")
            print("   git push")
            return True
        else:
            print("❌ Authentication failed!")
            print("Error:", result.stderr)

            # Try alternative method - store credentials manually
            print("\n🔄 Trying alternative authentication method...")

            # Create credential file
            cred_content = f"https://thainghia244:{token}@github.com"
            with open("C:\\Users\\Th4iNghia\\.git-credentials", "w") as f:
                f.write(cred_content + "\n")

            subprocess.run(["git", "config", "--global", "credential.helper", "store"],
                          check=True)

            # Test again
            result = subprocess.run(["git", "fetch", "origin"],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Alternative authentication successful!")
                return True
            else:
                print("❌ Alternative authentication also failed!")
                return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Error setting up authentication: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = setup_github_auth()
    if success:
        print("\n🎉 Setup complete! Try 'git push' now.")
    else:
        print("\n💡 Manual setup:")
        print("1. Run: git config --global credential.helper store")
        print("2. Run: git push")
        print("3. When prompted:")
        print("   Username: thainghia244")
        print("   Password: [your_token]")

    sys.exit(0 if success else 1)