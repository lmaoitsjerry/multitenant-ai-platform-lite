"""
Assign IP to Subuser

For production: Each client gets a dedicated IP (~$20-30/month)
For testing: Using shared parent IP
"""

import requests

# ============================================================
# CONFIGURATION
# ============================================================

MASTER_KEY = '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'
SUBUSER = 'africastay'

# ============================================================

def main():
    headers = {
        'Authorization': f'Bearer {MASTER_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Step 1: Get available IPs
    print('=' * 50)
    print('STEP 1: Getting available IPs...')
    print('=' * 50)
    
    resp = requests.get('https://api.sendgrid.com/v3/ips', headers=headers)
    
    if resp.status_code != 200:
        print(f'Error: {resp.text}')
        return
    
    ips = resp.json()
    print(f'Found {len(ips)} IP(s):')
    
    for ip in ips:
        ip_addr = ip.get('ip')
        pools = ip.get('pools', [])
        subusers = ip.get('subusers', [])
        print(f'  - {ip_addr}')
        print(f'    Pools: {pools}')
        print(f'    Subusers: {subusers}')
    
    if not ips:
        print('No IPs available!')
        return
    
    # Step 2: Assign first IP to subuser
    ip_address = ips[0].get('ip')
    
    print('')
    print('=' * 50)
    print(f'STEP 2: Assigning {ip_address} to {SUBUSER}...')
    print('=' * 50)
    
    resp = requests.post(
        f'https://api.sendgrid.com/v3/ips/{ip_address}/subusers',
        headers=headers,
        json={'subuser': SUBUSER}
    )
    
    print(f'Status: {resp.status_code}')
    
    if resp.status_code == 201:
        print('SUCCESS! IP assigned.')
        print(resp.json())
    elif resp.status_code == 200:
        print('SUCCESS! IP assigned.')
    else:
        print(f'Response: {resp.text}')
    
    # Step 3: Verify assignment
    print('')
    print('=' * 50)
    print('STEP 3: Verifying assignment...')
    print('=' * 50)
    
    resp = requests.get('https://api.sendgrid.com/v3/ips', headers=headers)
    if resp.status_code == 200:
        for ip in resp.json():
            if ip.get('ip') == ip_address:
                print(f"IP {ip_address} subusers: {ip.get('subusers', [])}")
                if SUBUSER in ip.get('subusers', []):
                    print(f'Confirmed: {SUBUSER} is assigned!')
    
    print('')
    print('=' * 50)
    print('NEXT: Re-run the test email to verify it sends')
    print('=' * 50)


if __name__ == '__main__':
    if 'PASTE_YOUR' in MASTER_KEY:
        print('ERROR: Edit this file and paste your SendGrid master key')
    else:
        main()
