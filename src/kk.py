#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import sqlite3

import cv2
import numpy as np
import requests
import matplotlib.pyplot as plt

from selenium import webdriver
from selenium.webdriver.common.keys import Keys


video_directory = 'videos'
frame_directory = 'frames'
database = 'friends.db'
delete_friend_button_name = 'Удалить из друзей'


# SEE: https://stackoverflow.com/questions/200309/sqlite-database-default-time-value-now
with sqlite3.connect(database) as conn:
  curr = conn.cursor()
  curr.execute(
    """
    CREATE TABLE IF NOT EXISTS friends (
      id INTEGER PRIMARY KEY,
      friend_name TEXT,
      friend_url TEXT,
      friend_avatar_url TEXT,
      t TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      deleted BOOLEAN DEFAULT 'f'
    )
    """
  )


def make_directory(directory: str):
  if not os.path.exists(directory):
    os.makedirs(directory)


def new_name(name: str):
  new = ''
  for char in os.path.splitext(name)[0]:
    new += char if char.isdigit() or char.isalpha() else '_'
  return new


class MCFriendParser:
  """Splitting video frames to images and this.images to squares as avatars

  Not fixed size of *squares so there will be trash with images (*squares).
  """
  def videos_to_frames(self):
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

  def crop_avatar_by_coordinates(self, imgray, frame_avatars_directory, avatar_name,
                                 x, y, w, h):
    """Need &imgray for other operations
    """
    crop_img = imgray[y:y+h, x:x+w]
    cv2.imwrite(os.path.join(frame_avatars_directory, avatar_name), crop_img)

  def dilated_contours(self, imgray):
    blurred = cv2.GaussianBlur(imgray, (3, 3), 0)
    canny = cv2.Canny(blurred, 20, 40)
    kernel = np.ones((3,3), np.uint8)
    return cv2.dilate(canny, kernel, iterations=2)

  def frames_to_avatars(self):
    """Spliting squares from frame
    """
    for video in os.listdir(frame_directory):
      # frames/video
      # XXX
      video_frames_directory = os.path.join(frame_directory, video, 'frames')
      frame_avatars_directory = os.path.join(frame_directory, video, 'avatars')

      make_directory(video_frames_directory)
      make_directory(frame_avatars_directory)

      for idx, _ in enumerate(os.listdir(video_frames_directory)):
        image_name = os.path.join(video_frames_directory, f"frame_{idx}.jpg")
        print('[+]', image_name)

        im = cv2.imread(image_name)
        imgray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)

        pro_image = self.dilated_contours(imgray)

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

            self.crop_avatar_by_coordinates(
              imgray, frame_avatars_directory, f"frame_{idx}_{avatar}.jpg",
              x, y, w, h
            )
            avatar += 1

  def parse(self):
    self.videos_to_frames()
    self.frames_to_avatars()


class Matching:
  """Template matching.
  """
  def match(self, fb_avatar_path):
    """Matching Facebook avatar with MonsterCastle avatars
    """
    # SEE: https://www.tutorialspoint.com/template-matching-using-opencv-in-python
    img1 = cv2.imread(fb_avatar_path)
    img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)

    matched = False

    for video in os.listdir(frame_directory):
      avatars_directory = os.path.join(frame_directory, new_name(video), 'avatars')
      for mc_avatar in os.listdir(avatars_directory):
        mc_avatar_path = os.path.join(avatars_directory, mc_avatar)

        img2 = cv2.imread(mc_avatar_path, 0)
        width, height = img2.shape[::-1]

        match = cv2.matchTemplate(img1_gray, img2, cv2.TM_CCOEFF_NORMED)
        threshold = 0.8
        position = np.where(match >= threshold)

        # TODO: Delete matched avatars

        if position[0].size:
          return True


print(Matching().match('test/match/target_to_match.jpg'))
exit()


class FBFriendParser:
  """Using selenium webdriver to manipulate with facebook web page.

  Just for test purposes. No API.
  """
  # SEE: https://github.com/mozilla/geckodriver/releases

  def __init__(self):
    # https://www.selenium.dev/documentation/en/webdriver/driver_requirements/
    self.driver = webdriver.Firefox()
    self.base_url = 'https://www.facebook.com/{}'
    self.driver.get(self.base_url.format('login'))

    # XXX
    # self.drvier.get(self.base_url.format('me'))
    # self.owner_friends_link = self.driver.current_url + 'friends'

    self.owner_friends_link = self.base_url.format('ames0k0/friends')

  def _log_friend_info(self, containers, fb_avatar_link) -> None:
    for container in containers:
      try:
        friend_page_url = div.find_element_by_tag_name('a')
        friend_name = friend_page_url.text
        friend_url = friend_page_url.get_attribute('href')

        with sqlite3.connect(database) as conn:
          curr.execute(
            f"""
            INSERT INTO friends (friend_name, friend_url, friend_avatar_url)
            VALUES ('{friend_name}', '{friend_url}', '{fb_avatar_link}')
            RETURNING id
            """
          )
          return curr.fetchone()[0]
      except:
        pass

  def _delete_friend(self, friend_id, containers):
    for container in containers:
      delete_event = container.get_attribute('aria-label')

      if delete_event is None:
        continue

      container.click()
      # XXX, let web to render it
      time.sleep(1)
      break

    delete_container = driver.find_element_by_css_selector('div[data-pagelet="root"]')
    action_events = delete_container.find_elements_by_css_selector('div[role="menuitem"]')

    for action in action_events:
      if action.text.strip() == delete_friend_button_name:
        # # TODO: enable
        # action.click()
        with sqlite3.connect(database) as conn:
          curr.execute(
            f"""
            UPDATE TABLE friends
            SET deleted = 't'
            WHERE id={friend_id}
            """
          )

        break

  def log_and_delete_friend(self, fb_avatar, fb_avatar_link):
    """Logging name and link to friend page.
    """
    # XXX: check &FBLoginTest.ipynb
    friend_data = fb_avatar.find_element_by_xpath('..').find_element_by_xpath('..').find_element_by_xpath('..')
    containers = friend_data.find_elements_by_tag_name('div')

    friend_id = self._log_friend_info(containers, fb_avatar_link)
    if friend_id is None:
      print('[!] Friend is not logged, so no deleted!')
      return None

    self._delete_friend(friend_id, containers)

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
    """Downloading mathing deleting and logging.
    """
    # SEE: https://www.tutorialspoint.com/downloading-files-from-web-using-python
    for aidx, avatar in enumerate(avatars):
      avatar_link = avatar.get_attribute('src')
      if avatar_link:
        response = requests.get(avatar_link)

        avatar_name = ''

        fb_avatar = os.path.join('test', 'avatars', f"avatar_{aidx}.jpg")
        with open(fb_avatar, 'wb') as ftw:
          ftw.write(response.content)

        # MATCHING HERE
        Matching.match(fb_avatar)

        self.log_and_delete_friend(avatar, avatar_link)

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
  # video -> frames -> avatars
  MCFriendParser().parse()

  # friends -> avatars -> !match -> delete -> log
  FBFriendParser().parse()


if __name__ == '__main__':
  main()

  # fbf = FBFriendParser()
  # fbf.login()
  # fbf.get_friends_avatar()

  # mch = Matching(os.path.join('test', 'match'))
  # mch.match('target_to_match.jpg', 'fake_dublicate.jpg')
  # mch.match('target_to_match.jpg', 'real_dublicate.jpg')
