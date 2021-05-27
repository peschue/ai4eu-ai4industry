# Planning AI4Industry

* PressCapUnit1 has two magazines which are filled with a sequence of blue/red caps, respectively.
* PressCapUnit2 has two magazines which are filled with a sequence of white/red caps, respectively.

Requirements => Offers : Machine

R = {RoundWorkpiece}

R => {BlueCap} : PressCapUnit1
R => {RedCap} : PressCapUnit1
R => {WhiteCap} : PressCapUnit2
R => {RedCap} : PressCapUnit2

# Testing

Test the server running in docker running
* `./scripts/test.py`.

Test without network (can be done in docker):
* call `main_test()` instead of `main()` at the end of `./src/ai4industry/app.py`.

