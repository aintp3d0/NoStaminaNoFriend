# NoStaminaNoFriend
Unfriend Facebook friends if not in the MonsterCastle game friend list.

### Script steps
- [x] Video to frames
- [x] Frame to avatars
- [x] Load Facebook friends avatar
- [x] Matching avatars
- [ ] Remove Facebook friend
- [ ] Report page to undo if script did something wrong ?


### NOTE
- Used my own page url: &owner_friends_link
- geckodriver PATH=$PATH:`pwd`/bin
- matching is too slow even with a &async or mc_avatar grabber doing a bad job


### TODO
- [ ] Join steps
- [ ] Improve mc_avatar grabber

```
videos/{video}.mp4
frames/{video}/frames/{frame}.jpg
frames/{video}/avatars/{frame}_{avatar}.jpg
frames/{video}/facebook/avatar_{avatar}.jpg
```
