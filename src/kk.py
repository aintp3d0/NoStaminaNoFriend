#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

import cv2
import numpy as np
import requests

from selenium import webdriver
from selenium.webdriver.common.keys import Keys


video_directory = 'videos'
frame_directory = 'frames'


class MCFriendParser:
  def make_directory(directory: str):
    if not os.path.exists(directory):
      os.makedirs(directory)

  def new_name(name: str):
    new = ''
    for char in os.path.splitext(name)[0]:
      new += char if char.isdigit() or char.isalpha() else '_'
    return new

  def videos_to_frames(limit: int = 1):
    # SEE: https://stackoverflow.com/a/33399711
    for vidx, video in enumerate(os.listdir(video_directory)):
      vidcap = cv2.VideoCapture(os.path.join(video_directory, video))
      success,image = vidcap.read()
      count = 0

      print(f"[!] Video to read: {video}")

      video_name = new_name(video)
      # *frames/video/frames
      image_directory = os.path.join(frame_directory, video_name, 'frames')
      make_directory(image_directory)

      while success:
        image_name = os.path.join(image_directory, f"frame_{count}.jpg")
        cv2.imwrite(image_name, image)
        success,image = vidcap.read()
        print('Read a new frame: ', success)
        count += 1

      if limit and limit == (vidx + 1):
        break

  def crop_avatar_by_coordinates(imgray, frame_avatars_directory, avatar_name,
                                 x, y, w, h):
    """Need &imgray for other operations
    """
    crop_img = imgray[y:y+h, x:x+w]
    cv2.imwrite(os.path.join(frame_avatars_directory, avatar_name), crop_img)

  def dilated_contours(imgray):
    blurred = cv2.GaussianBlur(imgray, (3, 3), 0)
    canny = cv2.Canny(blurred, 20, 40)
    kernel = np.ones((3,3), np.uint8)
    return cv2.dilate(canny, kernel, iterations=2)

  def frame_to_avatar():
    for video in os.listdir(frame_directory):
      # frames/video
      # XXX
      if video != 'mc_1_server':
        continue
      video_frames_directory = os.path.join(frame_directory, video, 'frames')
      frame_avatars_directory = os.path.join(frame_directory, video, 'avatars')

      make_directory(video_frames_directory)
      make_directory(frame_avatars_directory)

      for idx, _ in enumerate(os.listdir(video_frames_directory)):
        image_name = os.path.join(video_frames_directory, f"frame_{idx}.jpg")
        print('[+]', image_name)

        im = cv2.imread(image_name)
        imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        pro_image = dilated_contours(imgray)

        contours, hierarchy = cv2.findContours(
          pro_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        avatar = 0

        for c in contours:
          x, y, w, h = cv2.boundingRect(c)
          if w > 50 and h > 50:
            fe = abs((x+y) - (w+h))

            if fe > 500:
              continue

            if (fe < 100):
              continue

            if abs(w - h) > 100:
              continue

            crop_avatar_by_coordinates(
              imgray, frame_avatars_directory, f"frame_{idx}_{avatar}.jpg",
              x, y, w, h
            )
            avatar += 1


class FBFriendParser:
  """
  """
  # https://github.com/mozilla/geckodriver/releases

  def __init__(self):
    # https://www.selenium.dev/documentation/en/webdriver/driver_requirements/
    self.driver = webdriver.Firefox()
    self.base_url = 'https://www.facebook.com/{}'
    self.driver.get(self.base_url.format('login'))
    self.owner_friends_link = self.base_url.format('ames0k0/friends')

  def own_waiter(self, function, arg):
    while True:
      element = function(arg)
      if element is None:
        time.sleep(1)
      else:
        return element

  def _element_name(self, name):
    return self.driver.find_element_by_name(name)

  def _element_class(self, name):
    return self.driver.find_element_by_class_name(name)

  def _elements_tag(self, name):
    return self.driver.find_elements_by_tag_name(name)

  def _load_friends(self, no_arg):
    links = self.own_waiter(self._elements_tag, 'a')

    for link in links:
      if link.get_attribute('href') == self.owner_friends_link:
        return True

  def login(self):
    email = os.environ.get('FB_USER_EMAIL')
    pwd = os.environ.get('FB_USER_PWD')

    e_input = self.own_waiter(self._element_name, 'email')
    e_input.send_keys(email)

    p_input = self.own_waiter(self._element_name, 'pass')
    p_input.send_keys(pwd)

    l_button = self.own_waiter(self._element_name, 'login')
    l_button.click()

  def _download_fb_avatars(self, avatars):
    # SEE: https://www.tutorialspoint.com/downloading-files-from-web-using-python
    for aidx, avatar in enumerate(avatars):
      avatar_link = avatar.get_attribute('src')
      if avatar_link:
        response = requests.get(avatar_link)

        avatar_name = ''

        with open(os.path.join('test', 'avatars', f"avatar_{aidx}.jpg"), 'wb') as ftw:
          ftw.write(response.content)

  def _scroll_to_the_end(self):
    # NOTE: your internet connection will affect to this value
    SCROLL_PAUSE_TIME = 1.5
    # Get scroll height
    last_height = self.driver.execute_script("return document.body.scrollHeight")

    while True:
      # Scroll down to bottom
      self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

      # Wait to load page
      time.sleep(SCROLL_PAUSE_TIME)

      # Calculate new scroll height and compare with last scroll height
      new_height = self.driver.execute_script("return document.body.scrollHeight")
      if new_height == last_height:
        break
      last_height = new_height

  def get_friends_avatar(self):
    self.driver.get(self.owner_friends_link)
    _ = self.own_waiter(self._load_friends, 'No arg')

    self._scroll_to_the_end()

    avatars = self.own_waiter(self._elements_tag, 'img')
    self._download_fb_avatars(avatars)
    self.driver.close()

def main():
  # videos_to_frames(1)
  # frame_to_avatar()
  pass


if __name__ == '__main__':
  fbf = FBFriendParser()
  fbf.login()
  fbf.get_friends_avatar()
