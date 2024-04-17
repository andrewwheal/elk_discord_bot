# Todo

1. Update bot to be OO and use Extensions/Cogs
2. Get "old" bot working in new bootstrapping
3. Add info commands to easily find Channel IDs etc
4. Create new siege command, using slash commands with autocomplete
   1. How to autocomplete cities? How to manage this?

# Ideas from KoF: 

- ~~Language : add a reaction trigger effect (if you react with france emoji the message is translated in french) etc... 
  This will help bring down the language barrier~~
  - reaction added, but only works for a couple of languages where flag and lang codes match (e.g. FR, DE)
  - need to work out how to "translate" flags to langs
  - it can only translate from english... need to add language detection from the auto-translate

- Pre ping before siege : Bot will ping all the player that reacted ✅ and ❓ in the siege poll 5min before the siege
  - need to learn about scheduling tasks
    - is there any way we can reload them if the bot restarts?

- Making the list of members who are joining siege : Every member reacting with ✅ is considered participating and 
  will be added in a sheet/excell and we can check the amount of siege one player helped with the !siege command 
  (screen below as an exemple of how we were counting ticket used in my last game)
  - ![member contribution table](https://cdn.discordapp.com/attachments/1206953831586340977/1214590211531481219/image.png?ex=6602e4c8&is=65f06fc8&hm=c777f8293522f4ec0a9e71e82d8865482bb03f2cb5bcebcf08d2335bfe8ca1e4&) 

- Prepared answers in case : for exemple a !move region command that will explain the requirement to change region
  (only available for the member role or higher to avoid informations leak)

- A ticket system where any new player spawn in a personal channel (this is quite handy for recruitment interview 
  with no leaks)
  - it might come in handy if we have to manage many player, completely agree that's not a must-have now

- That's the few ideas i had ! Obviously not a rush but if you all like some of them i think that's worth trying to 
  implement this for the bot ! This should help us all managing the team 

- Allow editing a siege post, e.g. changing the time (alert people if it's delayed, but not edited soon after posting?)
