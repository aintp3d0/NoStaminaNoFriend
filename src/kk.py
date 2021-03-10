#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import sqlite3
from typing import Optional

import cv2
import numpy as np
import asyncio
import requests
import matplotlib.pyplot as plt

from selenium import webdriver
from selenium.webdriver.common.keys import Keys


database = 'friends.db'


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
      deleted BOOLEAN DEFAULT 'f',
      error_on_deletion BOOLEAN DEFAULT 'f'
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


def show_image(image):
  plt.imshow(image)
  plt.show()


video_directory = 'videos'
frame_directory = 'frames'
fb_avatar_dir = 'fb_avatars'
delete_friend_button_name = 'Удалить из друзей'


class Matching:
  """Template matching.
  """
  def crop_fb_avatar(self, fb_avatar):
    """Cropping image to make easy to match piece -20 margin.
    """
    # SEE: https://stackoverflow.com/a/15589825
    # LEFT
    x, y = (10, 10)
    crop_image = fb_avatar[x:, y:]
    # RIGHT
    crop_image = crop_image[:-x, :-y]
    return crop_image

  async def get_template(self, fb_avatar_path):
    img1 = cv2.imread(fb_avatar_path)
    img1_gray = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    return self.crop_fb_avatar(img1_gray)

  async def matches(self, img1_gray, img2):
    # NOTE: img1_gray.size > img.size

    try:
      match = cv2.matchTemplate(img1_gray, img2, cv2.TM_CCOEFF_NORMED)
    except Exception:
      return False

    threshold = 0.8
    position = np.where(match >= threshold)

    if position[0].size:
      return True

  async def not_main(self, fb_avatar_path):
    """Looking for a matches for this &fb_avatar_path

    Parameters
    ----------
    fb_avatar_path : str
      path to the fb_avatar
    remove_matches : bool
      Flag to remove matched &mc_avatar with &fb_avatar_path, default False
    """
    img1_gray = await self.get_template(fb_avatar_path)

    for video in os.listdir(frame_directory):
      avatars_directory = os.path.join(frame_directory, new_name(video), 'avatars')
      for mc_avatar in os.listdir(avatars_directory):
        mc_avatar_path = os.path.join(avatars_directory, mc_avatar)

        img2 = cv2.imread(mc_avatar_path, 0)
        mm = await self.matches(img1_gray, img2)
        if mm:
          return mm

  def match(self, fb_avatar_path) -> Optional[bool]:
    """Matching Facebook avatar with MonsterCastle avatars
    """
    return asyncio.run(self.not_main(fb_avatar_path))


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

  async def remove_duplicates(self):
    """Matching all &mc_avatar's with themselves.
    """
    print('[!] Removing duplicates')
    matching = Matching()

    for video in os.listdir(frame_directory):
      frame_avatars_directory = os.path.join(frame_directory, video, 'avatars')
      print('[+] Loaded', video)

      def get_mc_avatars():
        for avatar_name in os.listdir(frame_avatars_directory):
          mc_avatar_path = os.path.join(frame_avatars_directory, avatar_name)
          if os.path.exists(mc_avatar_path):
            yield mc_avatar_path

      for mc_avatar_path_as_p in get_mc_avatars():
        mc_avatar_p = await matching.get_template(mc_avatar_path_as_p)

        for mc_avatar_path_as_c in get_mc_avatars():
          # XXX: skip itself
          if mc_avatar_path_as_p == mc_avatar_path_as_c:
            continue

          mc_avatar_c = await matching.get_template(mc_avatar_path_as_c)

          if await matching.matches(mc_avatar_p, mc_avatar_c):
            os.remove(mc_avatar_path_as_c)

  def parse(self):
    """self.__doc__. Also removing duplicates
    """
    self.videos_to_frames()
    self.frames_to_avatars()

    asyncio.run(self.remove_duplicates())


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

  def wait_web_render(self, seconds=1):
    time.sleep(seconds)

  def _exit(self, message='Default Exit'):
    print(message)
    self.driver.close()
    exit()

  def _log_friend_info(self, containers, fb_avatar_link) -> None:
    """
    """

    def commit(friend_name, friend_url):
      with sqlite3.connect(database) as conn:
        curr = conn.cursor()
        curr.execute(
          f"""
          INSERT INTO
            friends (
              friend_name, friend_url, friend_avatar_url
            )
          VALUES
            (
              '{friend_name}', '{friend_url}', '{fb_avatar_link}'
            )
          """
        )
        conn.commit()
        return curr.lastrowid

    for container in containers:
      try:
        friend_page_url = container.find_element_by_tag_name('a')
        friend_name = friend_page_url.text
        friend_url = friend_page_url.get_attribute('href')

        if all((friend_name, friend_url)):
          return commit(friend_name, friend_url)

      except Exception:
        continue

  def _delete_friend(self, friend_id, containers):
    for container in containers:
      delete_event = container.get_attribute('aria-label')

      if delete_event is None:
        continue

      try:
        container.click()
      except Exception:
        pass

      self.wait_web_render()
      break

    delete_container = self.driver.find_element_by_css_selector('div[data-pagelet="root"]')
    action_events = delete_container.find_elements_by_css_selector('div[role="menuitem"]')

    for action in action_events:
      if action.text.strip() == delete_friend_button_name:

        action.click()
        self.wait_web_render()

        error_on_deletion = False
        confirm_deletion = self.driver.find_element_by_xpath(
          "//div[@aria-label='Подтвердить']"
        )

        if container:
          error_on_deletion = True
          confirm_deletion.click()

        with sqlite3.connect(database) as conn:
          curr = conn.cursor()
          curr.execute(
            f"""
            UPDATE
              friends
            SET
              deleted = 't', error_on_deletion={error_on_deletion}
            WHERE
              id={friend_id}
            """
          )

  def log_and_delete_friend(self, fb_avatar, fb_avatar_link):
    """Logging name and link to friend page.
    """
    # XXX: check research/&FBLoginTest.ipynb
    friend_data = fb_avatar.find_element_by_xpath('..').find_element_by_xpath('..').find_element_by_xpath('..')
    containers = friend_data.find_elements_by_tag_name('div')

    friend_id = self._log_friend_info(containers, fb_avatar_link)
    if friend_id is None:
      print('[!] Friend is not logged, so no deleted!')
      print('[-]', fb_avatar_link)
      return None

    self._delete_friend(friend_id, containers)

  def own_waiter(self, function, arg):
    while True:
      element = function(arg)
      if element is None:
        self.wait_web_render()
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
    # NOTE
    # Not filtered images, there is also a backgraound image.
    # Checking on logging.

    for aidx, avatar in enumerate(avatars[::-1]):
      avatar_link = avatar.get_attribute('src')
      if avatar_link:
        response = requests.get(avatar_link)

        make_directory(fb_avatar_dir)

        fb_avatar = os.path.join(fb_avatar_dir, f"avatar_{aidx}.jpg")
        with open(fb_avatar, 'wb') as ftw:
          ftw.write(response.content)

        # # XXX, MATCHING HERE
        matched = Matching().match(fb_avatar)
        if not matched:
          self.log_and_delete_friend(avatar, avatar_link)

  def _scroll_to_the_end(self):
    # NOTE: your internet connection will affect to this value
    SCROLL_PAUSE_TIME = 2.5
    # Get scroll height
    last_height = self.driver.execute_script("return document.body.scrollHeight")

    while True:
      # Scroll down to bottom
      self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

      # Wait to load page
      self.wait_web_render(SCROLL_PAUSE_TIME)

      # Calculate new scroll height and compare with last scroll height
      new_height = self.driver.execute_script("return document.body.scrollHeight")
      if new_height == last_height:
        break

      try:
        out_of_friends_section = self.driver.find_element_by_xpath(
          "//div[@data-pagelet='ProfileAppSection_1']"
        )
        if out_of_friends_section:
          break
      except Exception:
        pass

      last_height = new_height

  def get_friends_avatar(self):
    self.login()
    self.driver.get(self.owner_friends_link)
    _ = self.own_waiter(self._load_friends, 'No arg')

    self._scroll_to_the_end()

    avatars = self.own_waiter(self._elements_tag, 'img')
    self._download_fb_avatars(avatars)
    self.driver.close()


def main():
  # # XXX: video -> frames -> avatars
  MCFriendParser().parse()

  # # XXX: friends -> avatars -> !match -> delete -> log
  FBFriendParser().get_friends_avatar()


def match_test():
  for fb_avatar in os.listdir(fb_avatar_dir):
    fb_avatar = 'avatar_38.jpg'
    fb_avatar_path = os.path.join(fb_avatar_dir, fb_avatar)
    if os.path.isfile(fb_avatar_path):
      fb_ = cv2.imread(fb_avatar_path)
      if Matching().match(fb_avatar_path):
        print('MATCHED')

    print('NOT MATCHED', fb_avatar)


if __name__ == '__main__':
  main()

  # XXX: match_test()
