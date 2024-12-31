#!/bin/bash
# Simple script to check for mismatched extensions
# Created by Dr. Phil Polstra 
# for PentesterAcademy.com

find "$1" -print0 | while read -d $'\0' file
do
	resp=$(file "$file")
	filename=$(basename "$file")
	ext="${filename##*.}"
	# check for mismatch
	if [ "${ext^^}" == "PNG" ]; then
		if [[ ! $resp =~ "PNG image" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "JPG" ]; then
		if [[ ! $resp =~ "JPEG image" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "JPEG" ]; then
		if [[ ! $resp =~ "JPEG image" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "GIF" ]; then
		if [[ ! $resp =~ "GIF image" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "MP4" ]; then
		if [[ ! $resp =~ "MPEG v4" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "MP3" ]; then
		if [[ ! $resp =~ "MPEG" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "PDF" ]; then
		if [[ ! $resp =~ "PDF document" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "DOC" ]; then
		if [[ ! $resp =~ "Composite Document File" ]]; then
		   if [[ ! $resp =~ "Microsoft WinWord" ]]; then
			   echo "*** $filename is mismatched"
			   echo $resp
			fi
		fi
	elif [ "${ext^^}" == "DOCX" ]; then
		if [[ ! $resp =~ "Microsoft Word 2007" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "XLS" ]; then
		if [[ ! $resp =~ "Composite Document File" ]]; then
		   if [[ ! $resp =~ "Microsoft Excel" ]]; then
			   echo "*** $filename is mismatched"
			   echo $resp
			fi
		fi
	elif [ "${ext^^}" == "XLSX" ]; then
		if [[ ! $resp =~ "Microsoft Excel 2007" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "PPT" ]; then
		if [[ ! $resp =~ "Composite Document File" ]]; then
		   if [[ ! $resp =~ "Microsoft PowerPoint" ]]; then
			   echo "*** $filename is mismatched"
			   echo $resp
			fi
		fi
	elif [ "${ext^^}" == "PPTX" ]; then
		if [[ ! $resp =~ "Microsoft PowerPoint 2007" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	elif [ "${ext^^}" == "EXE" ]; then
		if [[ ! $resp =~ "executable" ]]; then
			echo "*** $filename is mismatched"
			echo $resp
		fi
	fi
	
done
