import os
import pickle
import cv2
import qrcode
import PIL
from PIL import Image
import json
import time
import pygame
import requests
import tkinter as tk
import google_auth_oauthlib.flow
from google_auth_oauthlib.flow import InstalledAppFlow
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
  
    qrr = qr.make_image(fill_color="black", back_color="white")
    type(qrr)
    qrr.save("selectionQR.png")
    return None


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


def resize_image(image, screen_width, screen_height):
    img_width, img_height = image.get_size()
    
    screen_aspect_ratio = screen_width/screen_height
    img_aspect_ratio = img_width/img_height
    
    new_height = screen_height
    new_width = screen_width
        
    return pygame.transform.scale(image, (new_width, new_height))
    


def crossfade(current_image, next_image, screen):
    alpha = 0
    while alpha < 255:
        current_image.set_alpha(255-alpha)
        next_image.set_alpha(alpha)
        
        screen.fill((0,0,0))
        screen.blit(current_image, (0,0))
        screen.blit(next_image, (0,0))
        
        pygame.display.flip()
        
        alpha+=1
        pygame.time.delay(60)


def display_images(images, screen, screen_width, screen_height):
    clock = pygame.time.Clock()
    index = 0
    
    current_image_path = os.path.join('images', images[index])
    current_image = pygame.image.load(current_image_path)
    current_image = resize_image(current_image, screen_width, screen_height)
    
    while True:
        next_index = (index + 1) % len(images)
        next_image_path = os.path.join('images', images[next_index])
        next_image = pygame.image.load(next_image_path)
        next_image = resize_image(next_image, screen_width, screen_height)
        crossfade(current_image, next_image, screen)
        
        current_image = next_image
        index = next_index
        
        #Controls how long image is on screen
        pygame.time.delay(2000)
        
        clock.tick(60)
        

def screen_init():
    pygame.init()
    displayInfo = pygame.display.Info()
    displayWidth = displayInfo.current_w
    displayHeight = displayInfo.current_h
    screen = pygame.display.set_mode((displayWidth, displayHeight),pygame.FULLSCREEN)
    return screen, displayWidth, displayHeight
    
    
def new_selection(credentials):
    session = create_session(creds)
    id_value = session.get('id')
    picker_uri = session.get('pickerUri')
    
    generate_qr_code(picker_uri)
    
    newUrl = "https://photospicker.googleapis.com/v1/sessions/"+id_value+"/mediaItems"
    
    screen, screenWidth, screenHeight = screen_init()
    codeDisplay = pygame.image.load("selectionQR.png")
    screen.blit(codeDisplay, (200, 200))
    pygame.display.flip()
    wait_for_selection(creds, id_value)
    pygame.display.quit()
    
    items = get_selected_items(creds, id_value)
    media_items = items.get('mediaItems', [])
    for item in media_items:
        base_url = item.get('mediaFile', {}).get('baseUrl')+"=d"
        download_images(item, base_url, creds.token)
    images = [f for f in os.listdir('images') if f.endswith(('.png', '.PNG', '.jpg', '.JPG', '.jpeg', '.JPEG', '.heic', '.HEIC'))]
    screen, screenWidth, screenHeight = screen_init()
    display_images(images, screen, screenWidth, screenHeight)
    pygame.display.quit()
    
    return None


if __name__ == '__main__':
    creds = authenticate_google_photos()
    new_selection(creds)
    
