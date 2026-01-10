
"""
Assign IP to Subuser - Alternative Method
"""

import requests

# ============================================================
# CONFIGURATION
# ============================================================

MASTER_KEY = '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'
SUBUSER = 'africastay'
IP_ADDRESS = '159.183.36.151'

# ============================================================

def main():
    headers = {
        'Authorization': f'Bearer {MASTER_KEY}',
        'Content-Type': 'application/json'
    }
    
    print('=' * 50)
    print('METHOD 1: PUT to subuser IPs endpoint')
    print('=' * 50)
    
    # Method 1: Update subuser's IPs
    resp = requests.put(
        f'https://api.sendgrid.com/v3/subusers/{SUBUSER}/ips',
        headers=headers,
        json=[IP_ADDRESS]
    )
    
    print(f'Status: {resp.status_code}')
    print(f'Response: {resp.text}')
    
    if resp.status_code in [200, 201]:
        print('SUCCESS!')
    else:
        print('')
        print('=' * 50)
        print('METHOD 2: Check subuser details')
        print('=' * 50)
        
        # Get subuser info
        resp = requests.get(
            f'https://api.sendgrid.com/v3/subusers/{SUBUSER}',
            headers=headers
        )
        print(f'Subuser info status: {resp.status_code}')
        print(f'Response: {resp.text}')
        
        print('')
        print('=' * 50)
        print('METHOD 3: List all subusers with IPs')
        print('=' * 50)
        
        resp = requests.get(
            'https://api.sendgrid.com/v3/subusers?limit=100',
            headers=headers
        )
        print(f'Status: {resp.status_code}')
        if resp.status_code == 200:
            for sub in resp.json():
                print(f"  - {sub.get('username')}: IPs = {sub.get('ips', [])}")
    
    # Verify
    print('')
    print('=' * 50)
    print('Checking subuser IPs...')
    print('=' * 50)
    
    resp = requests.get(
        f'https://api.sendgrid.com/v3/subusers/{SUBUSER}',
        headers=headers
    )
    if resp.status_code == 200:
        data = resp.json()
        print(f"Subuser: {SUBUSER}")
        print(f"IPs assigned: {data}")


if __name__ == '__main__':
    if 'PASTE_YOUR' in MASTER_KEY:
        print('ERROR: Edit this file and paste your SendGrid master key')
    else:
        main()
