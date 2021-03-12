# pyF1Viewer

pyF1Viewer is similar to https://github.com/SoMuchForSubtlety/f1viewer except written in Python and worse.

This is mostly a proof of concept for the new 2021 F1TV API.

## How to use
You'll need the `requests` library, that's about it in the way of requirements.

Run the file, sorry - it doesn't save your username and password but it does save your auth token for ~23 hours - you still need ot use the Login option everytime you run it even if you've given it credentials within 23 hours.

As you can see from the demo below it currently allows typing in a year number; there is currently functionality for back to 2018 and forwards into 2021 (yes, it works with live showings). I'm working on proper F1TV Archive Support.

## Warning
This has pretty much no error checking, it will just crash if there's a problem

### Demo using an additional stream from Austria 2020

https://streamable.com/03ercb