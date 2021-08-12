def progress(count, total, status=''):
    # adapted from https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))
    bar = '[' + '=' * filled_len + '-' * (bar_len - filled_len) + ']'
    myBar = bar + " " + str(count) + "/" + str(total) + " seconds remaining for " + status + "!"
    print(myBar)

if __name__ == "__main__":
    progress(300, 500, "White")