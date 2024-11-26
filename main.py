import os
import pickle
import cv2
import qrcode
from PIL import Image
import json
import time
import requests
import google_auth_oauthlib.flow
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

# If modifying the scope, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/photospicker.mediaitems.readonly']



def generate_qr_code(data):
    #Creates a qr code of the link to select photos
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill='black', back_color='white')


def authenticate_google_photos():
    #Authenticate and authorize the user to access their Google Photos
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('Credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)  # Open a local server for OAuth
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds


def create_session(creds):
    #This function creates an api session *Maybe only run it once?
    url = 'https://photospicker.googleapis.com/v1/sessions'
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-Type':'application/json'
    }

    response = requests.post(url, headers=headers)

    if response.status_code == 200:
        print("Session created successfully")
        print(json.dumps(response.json(), indent=2))
    else:
        print(f'Failed to create session. Status code: {response.status_code}')
        print(response)

    response = response.json()
    return response


def get_selected_items(creds, id_val):
    #This function gets the list of the selected images & their info
    url = "https://photospicker.googleapis.com/v1/mediaItems"
    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-Type': 'application/json'
    }
    params = {
        'sessionId': id_val
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        print('Selected items retrieved successfully:')
        print(json.dumps(response.json(), indent=2))
    else:
        print(f'Failed to retrieve items. Status code: {response.status_code}')
    response = response.json()
    return response


def download_images(item, url, token):
    #This function downloads the images to the images folder in this directory
    fileName = item.get('mediaFile', {}).get('filename')
    file_path = os.path.join('images', fileName)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type':'application/json'
    }
    response = requests.get(url, headers=headers, stream=True)
    if response.status_code == 200:
        with open(file_path, 'wb') as file:
            file.write(response.content)


def wait_for_selection(creds, id):
    #This function delays the rest of the code until the user selects their photos (Max of 2000 seconds)
    url = f"https://photospicker.googleapis.com/v1/sessions/"+id

    headers = {
        'Authorization': f'Bearer {creds.token}',
        'Content-Type': 'application/json'
    }
    elapsed_time = 0
    while elapsed_time < 2000:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            session_data = response.json()
            media_items_set = session_data.get('mediaItemsSet', False)
            if media_items_set:
                print("User has selected media items.")
                return session_data
            else:
                print(f"Waiting for 5 seconds before polling again.")
                time.sleep(5)
                elapsed_time += 5
        else:
            print(f"Failed to poll session. Status code: {response.status_code}")
            break
    return None


def load_images(folder):
    return [cv2.imread(os.path.join('images', img))
            for img in os.listdir(folder) if img.endswith(('PNG', 'JPG', 'JPEG', 'HEIC'))]

def display_images(images):
    index = 0
    alpha = 1.0
    beta = 0.0

    # Create a window to display the slideshow
    cv2.namedWindow("Slideshow", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Slideshow", 800, 600)

    while True:
        img1 = cv2.resize(images[index % len(images)], (800, 600))
        img2 = cv2.resize(images[(index + 1) % len(images)], (800, 600))

        alpha -= 0.01
        beta += 0.01

        # Blend the two images
        blended = cv2.addWeighted(img1, alpha, img2, beta, 0)
        cv2.imshow("Slideshow", blended)

        # Reset alpha and beta for the next transition
        if alpha <= 0:
            alpha, beta = 1.0, 0.0
            index += 1  # Move to the next image
            cv2.waitKey(5000)

        # Press 'q' to exit the slideshow
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == '__main__':
    creds = authenticate_google_photos()
    session = create_session(creds)
    id_value = session.get('id')
    picker_uri = session.get('pickerUri')
    qr = generate_qr_code(picker_uri)
    newUrl = "https://photospicker.googleapis.com/v1/sessions/"+id_value+"/mediaItems"
    qr.show()
    wait_for_selection(creds, id_value)
    qr.close()
    items = get_selected_items(creds, id_value)
    media_items = items.get('mediaItems', [])
    for item in media_items:
        base_url = item.get('mediaFile', {}).get('baseUrl')+"=d"
        download_images(item, base_url, creds.token)
    images = load_images('images')
    print(images)
    display_images(images)
