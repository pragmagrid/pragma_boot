#!/bin/bash



image_name=$1

virsh undefine $image_name
virsh vol-list transferimages
virsh vol-delete $image_name  --pool transferimages

