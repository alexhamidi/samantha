import requests
import json
import time
from pathlib import Path

def upload_audio(audio_file_path, cookies=None):
    """Upload audio file and return the media ID"""
    
    url = "https://aidemos.meta.com/api/graphql/"
    
    # Default cookies - update these with fresh ones from your browser
    if cookies is None:
        cookies = {
            'datr': 'UB9LaSTV0oaTX-YJ3HRGEzp5',
            'fair_csrf': 'rHK_3WOlAlaHZlfbbOPKaD',
            'ps_l': '1',
            'ps_n': '1'
        }
    
    # Headers - NOTE: We let requests handle decompression automatically
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,la;q=0.8',
        'origin': 'https://aidemos.meta.com',
        'priority': 'u=1, i',
        'referer': 'https://aidemos.meta.com/segment-anything/editor/segment-audio',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.170", "Chromium";v="143.0.7499.170", "Not A(Brand";v="24.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-fb-lsd': 'AdFAEbnOoLU'
    }
    
    # Prepare the file
    audio_path = Path(audio_file_path)
    filename = audio_path.name
    
    files = {
        'file': (filename, open(audio_path, 'rb'), 'audio/mpeg')
    }
    
    # Form data
    data = {
        'av': '0',
        '__user': '0',
        '__a': '1',
        '__req': '5',
        '__hs': '20459.HYP:ai_demos_pkg.2.1...0',
        'dpr': '3',
        '__ccg': 'EXCELLENT',
        '__rev': '1031692191',
        '__s': '64o9sl:ayom5n:8irn2r',
        '__hsi': '7592382894297000645',
        '__dyn': '7xeUmwlE7ibwKBAg5S1Dxu13w8CewSwMwNw9G2S0lW4o0B-q1ew6ywaq0yE7i0n24oaEd82lwv89k2C1Fwc60D85m1mxe0EUjwGzE2ZwNwmE2eUlwhE2Lw6OyES0gq0Lo6-3u362q0XU6O1FwlU6S0IUuwm85K0UE3Dw4Pw',
        '__csr': 'gglGQitXGiAq22uCqQqHwaKU01vJAKii1VK0nt4K0eOUbhsE2qA4G5k5PIg0z81nA0gzw1r-Uow2hU620JHxK0jZ0fS2h02EQ0cyw21UDw95wpU42PwCg1dFyxjJ6o551wnei8BgsogC5UEc38K0Ok2D4wu81tk1vN4iElk8Ic0Z4wu87oOCg77wU82u00ylQUOA7K0f5K4Fkl0Qwg82Jw',
        '__hsdp': 'gbOcxsjBRkayiA492k6ki9w6Kw8u1nxG1lg',
        '__hblp': '08y5oO4HwwCyo7Gfw4myK58Wq1kDxV0AxaEiAK3edAyUbU',
        '__sjsp': 'gbOnEn4anlgG9aggA9gph8',
        '__comet_req': '62',
        'lsd': 'AdFAEbnOoLU',
        'jazoest': '2928',
        '__spin_r': '1031692191',
        '__spin_b': 'trunk',
        '__spin_t': '1767739396',
        '__jssesw': '1',
        '__crn': 'comet.aidemos.SAMAudioDemoRoute'
    }
    
    # Create session
    session = requests.Session()
    session.cookies.update(cookies)
    
    try:
        print(f"Uploading {filename}...")
        response = session.post(url, headers=headers, files=files, data=data, timeout=120)
        
        files['file'][1].close()
        
        if response.status_code == 200:
            print(f"✓ Upload successful (Status: {response.status_code})")
            
            # Get the decompressed text (requests handles this automatically)
            response_text = response.text
            
            print(f"Response length: {len(response_text)} chars")
            print(f"Response preview: {response_text[:200]}")
            
            # Meta often returns newline-delimited JSON
            for line in response_text.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    media_id = extract_id_from_response(data)
                    if media_id:
                        print(f"✓ Media ID: {media_id}")
                        return media_id, session
                except json.JSONDecodeError as e:
                    print(f"  JSON parse error on line: {e}")
                    continue
            
            print("⚠ Could not extract media ID from response")
            return None, session
        else:
            print(f"✗ Upload failed (Status: {response.status_code})")
            print(f"Response: {response.text[:500]}")
            return None, session
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
        return None, None


def extract_id_from_response(data):
    """Recursively search for ID in response data"""
    if isinstance(data, dict):
        # Look for media or file IDs
        if 'id' in data and isinstance(data['id'], str):
            # Make sure it's a numeric ID
            if data['id'].isdigit() or len(data['id']) > 10:
                return data['id']
        
        # Check common GraphQL response patterns
        if 'data' in data:
            result = extract_id_from_response(data['data'])
            if result:
                return result
        
        # Recursively check all values
        for key, value in data.items():
            if key in ['id', 'media_id', 'file_id', 'upload_id']:
                if isinstance(value, str) and (value.isdigit() or len(value) > 10):
                    return value
            result = extract_id_from_response(value)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = extract_id_from_response(item)
            if result:
                return result
    return None


def check_processing_status(data):
    """Check if processing is complete, in progress, or errored"""
    if isinstance(data, dict):
        # Look for status indicators
        if 'status' in data:
            status = str(data['status']).lower()
            if 'complete' in status or 'ready' in status or 'success' in status:
                return 'complete'
            elif 'error' in status or 'fail' in status:
                return 'error'
            elif 'processing' in status or 'pending' in status:
                return 'processing'
        
        # Check nested structures
        for value in data.values():
            result = check_processing_status(value)
            if result:
                return result
                
    elif isinstance(data, list):
        for item in data:
            result = check_processing_status(item)
            if result:
                return result
    
    return None


def poll_upload_status(session, media_id, max_attempts=30, interval=2):
    """Poll the upload status until processing is complete"""
    
    url = "https://aidemos.meta.com/api/graphql/"
    
    # Headers for polling
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,la;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://aidemos.meta.com',
        'priority': 'u=1, i',
        'referer': 'https://aidemos.meta.com/segment-anything/editor/segment-audio',
        'sec-ch-prefers-color-scheme': 'dark',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-full-version-list': '"Google Chrome";v="143.0.7499.170", "Chromium";v="143.0.7499.170", "Not A(Brand";v="24.0.0.0"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-platform-version': '"26.0.1"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-asbd-id': '359341',
        'x-fb-friendly-name': 'useSAMUploadMediaQuery',
        'x-fb-lsd': 'AdFAEbnOoLU'
    }
    
    # Polling data
    data = {
        'av': '0',
        '__user': '0',
        '__a': '1',
        '__req': 'b',
        '__hs': '20459.HYP:ai_demos_pkg.2.1...0',
        'dpr': '3',
        '__ccg': 'EXCELLENT',
        '__rev': '1031692191',
        '__s': '64o9sl:ayom5n:8irn2r',
        '__hsi': '7592382894297000645',
        '__dyn': '7xeUmwlE7ibwKBAg5S1Dxu13w8CewSwMwNw9G2S0lW4o0B-q1ew6ywaq0yE7i0n24oaEd82lwv89k2C1Fwc60D85m1mxe0EUjwGzE2ZwNwmE2eUlwhE2Lw6OyES0gq0Lo6-3u362q0XU6O1FwlU6S0IUuwm85K0UE3Dw4Pw',
        '__csr': 'gglGQitXGiAq22uCqQqHwaKU01vJAKii1VK0nt4K0eOUbhsE2qA4G5k5PIg0z81nA0gzw1r-Uow2hU620JHxK0jZ0fS2h02EQ0cyw21UDw95wpU42PwCg1dFyxjJ6o551wnei8BgsogC5UEc38K0Ok2D4wu81tk1vN4iElk8Ic0Z4wu87oOCg77wU82u00ylQUOA7K0f5K4Fkl0Qwg82Jw',
        '__hsdp': 'gbOcxsjBRkayiA492k6ki9w6Kw8u1nxG1lg',
        '__hblp': '08y5oO4HwwCyo7Gfw4myK58Wq1kDxV0AxaEiAK3edAyUbU',
        '__sjsp': 'gbOnEn4anlgG9aggA9gph8',
        '__comet_req': '62',
        'lsd': 'AdFAEbnOoLU',
        'jazoest': '2928',
        '__spin_r': '1031692191',
        '__spin_b': 'trunk',
        '__spin_t': '1767739396',
        '__jssesw': '1',
        '__crn': 'comet.aidemos.SAMAudioDemoRoute',
        'fb_api_caller_class': 'RelayModern',
        'fb_api_req_friendly_name': 'useSAMUploadMediaQuery',
        'server_timestamps': 'true',
        'variables': json.dumps({"id": media_id}),
        'doc_id': '25521794540750262'
    }
    
    print(f"\nPolling upload status for ID: {media_id}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"  Attempt {attempt}/{max_attempts}...", end=' ')
            
            response = session.post(url, headers=headers, data=data, timeout=30)
            
            if response.status_code == 200:
                response_text = response.text
                
                # Parse response to check status
                for line in response_text.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        response_data = json.loads(line)
                        
                        status = check_processing_status(response_data)
                        
                        if status == 'complete':
                            print("✓ Processing complete!")
                            return True, response_data
                        elif status == 'error':
                            print("✗ Processing error")
                            return False, response_data
                        elif status == 'processing':
                            print("⏳ Still processing...")
                            
                    except json.JSONDecodeError:
                        continue
                
                # If we couldn't determine status, wait and retry
                print("⏳ Status unclear, retrying...")
                
            else:
                print(f"✗ Request failed (Status: {response.status_code})")
            
            if attempt < max_attempts:
                time.sleep(interval)
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Error: {e}")
            if attempt < max_attempts:
                time.sleep(interval)
    
    print(f"\n⚠ Max polling attempts ({max_attempts}) reached")
    return False, None


def main():
    # Configuration
    audio_file = "data/sunday.mp3"  # Replace with your audio file
    
    if not Path(audio_file).exists():
        print(f"Error: File '{audio_file}' not found")
        return
    
    # Step 1: Upload audio
    media_id, session = upload_audio(audio_file)
    
    if not media_id or not session:
        print("✗ Upload failed, cannot poll status")
        return
    
    # Step 2: Poll for completion
    success, result = poll_upload_status(
        session,
        media_id,
        max_attempts=30,
        interval=2
    )
    
    if success:
        print("\n✓ Audio processing completed successfully!")
        print("\nFinal result:")
        print(json.dumps(result, indent=2))
    else:
        print("\n✗ Audio processing did not complete")


if __name__ == "__main__":
    main()