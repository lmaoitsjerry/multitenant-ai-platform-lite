"""
Fix Verified Sender Script

This will:
1. List existing senders under africastay subuser
2. Delete any unverified ones
3. Create a fresh verified sender
4. Trigger verification email
"""

import requests
import json

# ============================================================
# CONFIGURATION - UPDATE THIS
# ============================================================

MASTER_KEY = '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'

# ============================================================

BASE_URL = 'https://api.sendgrid.com/v3'

def main():
    headers = {
        'Authorization': f'Bearer {MASTER_KEY}',
        'Content-Type': 'application/json',
        'on-behalf-of': 'africastay'  # Operate as the subuser
    }
    
    # Step 1: List existing verified senders
    print('=' * 50)
    print('STEP 1: Checking existing senders...')
    print('=' * 50)
    
    resp = requests.get(f'{BASE_URL}/verified_senders', headers=headers)
    print(f'Status: {resp.status_code}')
    
    if resp.status_code == 200:
        senders = resp.json().get('results', [])
        print(f'Found {len(senders)} sender(s)')
        
        for s in senders:
            sender_id = s.get('id')
            from_email = s.get('from_email')
            verified = s.get('verified')
            print(f'  - ID: {sender_id} | Email: {from_email} | Verified: {verified}')
        
        # Delete any unverified senders
        for s in senders:
            if not s.get('verified'):
                sender_id = s.get('id')
                print(f'')
                print(f'Deleting unverified sender ID {sender_id}...')
                del_resp = requests.delete(
                    f'{BASE_URL}/verified_senders/{sender_id}', 
                    headers=headers
                )
                print(f'Delete status: {del_resp.status_code}')
    else:
        print(f'Error: {resp.text}')
    
    # Step 2: Create fresh verified sender
    print('')
    print('=' * 50)
    print('STEP 2: Creating verified sender...')
    print('=' * 50)
    
    sender_data = {
        'nickname': 'Zorah Test Sender',
        'from_email': 'mail.test@zorah.ai',
        'from_name': 'Zorah AI',
        'reply_to': 'mail.test@zorah.ai',
        'reply_to_name': 'Zorah AI',
        'address': '123 Main Road',
        'city': 'Johannesburg',
        'country': 'South Africa'
    }
    
    resp = requests.post(
        f'{BASE_URL}/verified_senders',
        headers=headers,
        json=sender_data
    )
    
    print(f'Status: {resp.status_code}')
    
    if resp.status_code in [200, 201]:
        print('SUCCESS! Verified sender created.')
        print(json.dumps(resp.json(), indent=2))
        print('')
        print('=' * 50)
        print('NEXT STEP:')
        print('Check mail.test@zorah.ai inbox')
        print('Click the "Verify Single Sender" button in the email')
        print('=' * 50)
    elif resp.status_code == 400 and 'already exists' in resp.text.lower():
        print('Sender already exists.')
        print('Resending verification email...')
        
        # Try to resend verification
        resend_resp = requests.post(
            f'{BASE_URL}/verified_senders/resend/mail.test@zorah.ai',
            headers=headers
        )
        print(f'Resend status: {resend_resp.status_code}')
        if resend_resp.status_code == 200:
            print('Verification email resent! Check inbox.')
    else:
        print(f'Error: {resp.text}')


if __name__ == '__main__':
    if 'PASTE_YOUR' in MASTER_KEY:
        print('ERROR: Please edit this file and paste your SendGrid master key!')
        print('Open scripts/fix_sender.py and update MASTER_KEY')
    else:
        main()
