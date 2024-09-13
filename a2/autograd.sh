#!/bin/bash
DEST_DIR="/Users/jaskaransinghbhalla/Work/courses/col334/a2/autograd/submissions/"
FOLDER_NAME="tt1211139_tt1211175"
cp -r "./code" "./$FOLDER_NAME"
zip -r  "./submission/$FOLDER_NAME" "./$FOLDER_NAME"
cp "./submission/$FOLDER_NAME.zip" "$DEST_DIR"
rm -rf "./$FOLDER_NAME"
echo "Folder zipped and moved successfully."
# ./autograd/autograd/run.sh 
# echo "Autograd run successfully."