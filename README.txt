Floating Mosaic Grid 2.0 for Stash
==================================

Floating Mosaic Grid is a UI-only Stash plugin that displays the current
scene as an always-on-top, resizable and clickable contact sheet. It works
independently from Mosaic Poster and may remain installed alongside it.

FEATURES
- Selectable 4x4, 5x5, 6x6, 7x7 and 8x8 floating grids.
- Uses Stash's existing sprite image and WebVTT timestamps.
- Clicking a frame seeks the main Stash video and keeps keyboard control in
  the floating window.
- Left/Right Arrow seeks backward or forward five seconds without pausing.
- Hold Ctrl and use any arrow key to move a highlighted grid selection without
  seeking; release Ctrl to seek there and start playback.
- Opens automatically on the first normal player click by default.
- Ctrl+Shift+M provides an invisible manual opening shortcut.
- No fixed page button, leaving Stash's Multiview control unobscured.
- Prevents duplicate floating windows and unexpected automatic reopening.
- After the floater is closed, automatic reopening is suppressed until the
  Stash page is fully reloaded. Ctrl+Shift+M can still reopen it intentionally.
- Keeps the same floating window and refreshes it across scene navigation.
- Remembers the selected grid size in the browser.
- Does not generate media, run ffmpeg or modify Stash metadata.

REQUIREMENTS
- Stash sprites generated for each scene you want to display.
- Current Chrome or Edge desktop with Document Picture-in-Picture support.
- Stash opened through http://localhost:9980 or HTTPS. Plain HTTP through a
  remote address may not provide the secure context required by Document PiP.

INSTALLATION
1. Extract the ZIP.
2. Copy the enclosed MosaicFloat6x6 folder into the Stash plugins folder.
   The final manifest path must be:
   .../plugins/MosaicFloat6x6/MosaicFloat6x6.yml
3. In Stash, open Settings -> Plugins and select Reload plugins.
4. Refresh the Stash browser page.
5. Open a scene and make a normal left-click in the video player. The floating
   grid opens together with that first player gesture.

UPGRADING FROM VERSION 1.0
Replace the existing MosaicFloat6x6 plugin folder with the folder from this
release, reload plugins in Stash, and refresh the browser page. The plugin ID
and installation folder remain unchanged.

USE
- Select 4x4 through 8x8 using the buttons at the top of the floater.
- Click a frame to seek the main video.
- Press Left/Right Arrow in the floater to seek by five seconds.
- Hold Ctrl and move with Left/Right/Up/Down Arrow. Release Ctrl to seek to the
  highlighted frame and start playback.
- Press Ctrl+Shift+M on the Stash scene page if you need to open the floater
  manually.
- Resize or move the floating window with the normal browser controls.

SETTING
Automatic opening is enabled by default because the plugin intentionally has
no page button. Enable 'Disable automatic opening' in the plugin settings if
you want player clicks to leave the floater closed. Ctrl+Shift+M remains
available as the manual opening route. Refresh the Stash page after changing
the setting.

TESTING CHECKLIST
1. Reload Stash, open a scene and click the player. Verify exactly one floating
   window opens and normal playback behavior continues.
2. Click the player repeatedly and verify no duplicate window opens.
3. Test every grid size from 4x4 through 8x8 and click frames in each view.
4. With the floater focused, test Left/Right Arrow seeking and verify the video
   is not paused by an extra main-player click.
5. Hold Ctrl, move the yellow selection with all four arrow keys, and release
   Ctrl. Verify seeking occurs only on release and playback starts there.
6. Navigate to another scene without reloading and verify the existing
   floating window updates when sprite data becomes available.
7. Close the floater and click the player again. Verify it does not reopen
   automatically during that page lifetime.
8. Press Ctrl+Shift+M and verify the floater reopens intentionally.
9. Enable 'Disable automatic opening', refresh Stash, and verify player clicks
   do not open it while Ctrl+Shift+M still does.
10. Verify no plugin launcher covers Stash's Multiview control.

TROUBLESHOOTING
- If the floater does not appear, press Ctrl+Shift+M while viewing a scene.
- If it reports that it is waiting for sprite data, run Generate -> Sprites
  for that scene and reload it.
- Keep the source Stash tab open; Chrome closes Document PiP with its source.
- Document PiP requires a supported browser and a secure context.

REMOVE
Delete the MosaicFloat6x6 folder from the Stash plugins directory, reload
plugins, and refresh the browser page.

CREDIT
Thanks to the Mosaic Poster developer for suggesting automatic opening on the
first player click and providing the original lifecycle sketch. Version 2.0
uses an independent sprite/WebVTT renderer so every grid size is accurate,
while preserving the suggested capture-phase browser user-gesture approach.
