on open droppedItems
    repeat with anItem in droppedItems
        set p to POSIX path of anItem
        do shell script quoted form of "/Users/john/1031_Hauntimator/Hauntimator" & " -f " & quoted form of p
    end repeat
end open

on run
    do shell script quoted form of "/Users/john/1031_Hauntimator/Hauntimator"
end run

