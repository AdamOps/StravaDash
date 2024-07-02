This is a work in progress for an app that fetches Strava athlete/activity data and lets the user do cool things with it.
Currently, it does the following:
- Redirect the user to an OAUTH page upon clicking a button
- Get an authorization token -> access/refresh token
- Fetch a couple of activities from the past week (NB: No check yet if the athlete wasn't active during this time)
- Fetch the activity streams belonging to these above activities, in LatLng format
- Generate polylines on a Folium map for these activities, and toss it into a simple html file
- Display the map on the main Dash page again

Basic intended features to add:
- Progress charts on best efforts for chosen distances
- Equipment usage (e.g. shoe mileage) over time

More advanced features
- Auto-classify runs based on activity data. E.g., recognise interval runs, tempo runs, or long runs based on surrounding user activity or data variability.
- Predict race times based on recent exercise performance (e.g. using some sort of MA model)
