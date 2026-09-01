---
name: roll-dice
description: Use this skill for dice, games, numbers, randomness, chance and probability.
---

# Roll Dice

Use the following command to roll a die:

```bash
echo $(( RANDOM % <sides> + 1 ))
```

Replace `<sides>` with the number of sides on the die, such as `6` for a d6 or `20` for a d20.
