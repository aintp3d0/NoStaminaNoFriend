#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sqlite3
from contextlib import contextmanager
from collections import namedtuple


database = 'friends.db'
export_page = 'index.html'
colors = ['red', 'blue']
Friend = namedtuple(
  'Friends', [
    'id', 'name', 'url', 'avatar_url', 'added_at', 'deleted', 'error_on_delete'
  ]
)


@contextmanager
def export_deleted_friends():
  try:
    file = open(export_page, 'w')
    file.write(
      """
      <DOCTYPE html>
      <html>
        <head>
          <title>Removed Facebook Friends</title>
        </head>
        <body>
      """
    )
    yield file
  finally:
    file.write(
      """
        </body>
      </html>
      """
    )
    file.close()


def get_friends_list(curr, func, ftw):
  curr.execute('select * from friends')
  for idx, friend in enumerate(curr.fetchall()):
    friend = Friend(*friend)
    color = colors[idx%2]
    if func(friend):
      ftw.write(
        f"""
        <div id={friend.id} style="margin-bottom: 10px; border: 1px solid {color}">
          <p style="margin-top: 0px; margin-bottom: 0px;">Name: {friend.name}</p>
          <img src={friend.avatar_url} />
          <span>Deleted at: {friend.added_at}</span>
          <button><a target="_blank" href={friend.url}>Visit</a></button>
        </div>
        """
      )

def deleted_friends(friend):
  if friend.deleted:
    return True


if __name__ == '__main__':
  with sqlite3.connect(database) as conn:
    curr = conn.cursor()

    with export_deleted_friends() as ftw:
      get_friends_list(curr, deleted_friends, ftw)
