# NoStaminaNoFriend
Unfriend Facebook friends if not in the MonsterCastle game friend list.

```
Put vidoes on:
  videos/{video}.mp4

Generates frames to:
  frames/{video}/frames/{frame}.jpg

Generates avatars from frames to:
  frames/{video}/avatars/{frame}_{avatar}.jpg

Putting Facebook Friends avatar to:
  fb_avatars/avatar_{avatar}.jpg
```



### Frame parsing
- [ ] Frame to FaceBook friends profile


### Functions
- [ ] FaceBook friend list loader


### Script steps
- [x] Video to frames
- [ ] Frame to fb friends profile
- [x] Frame to avatars
- [x] Load Facebook friends avatar
- [x] Matching avatars
- [x] Remove Facebook friend
- [x] Report page to undo if script did something wrong ?


### NOTE
- Used my own page url: &owner_friends_link
- geckodriver PATH=$PATH:`pwd`/bin
- Matching is too slow even with a &async or mc_avatar grabber doing a bad job
- Need better avatar to match with tiny version of it


### TODO
- [x] Join steps
- [ ] Improve mc_avatar grabber
- [ ] Make this repository as a one of the function for this game.



##### RECORDS
- [ ] Blog: Waiting for @ArutairuMup/holopsicon
- [x] Video: https://www.youtube.com/playlist?list=PL3HqI3Rgp3qi30z46yXQVi5TtAswUCfHL


```
[ CHANGES ]
- image
  - no reshape


[ STEPS ]
- frames
  + getting frames from video
  + frames to avatars
  + deleting avatar duplicates
- fb_avatars
  + getting avatars
    + all friends avatar (with scroll)
  + matching &fb_avatar with &mc_avatars
  + deletion
    + logging deleted fb_friends
```
