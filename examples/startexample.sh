#!/bin/bash
EXAMPLES="custom oneprice simple staggered generic"
PLATAMODULES="contact discount shop"

echo Welcome to Plata’s examples!

if [ ! -d "staggered" ]; then
    echo It seems we’re not in the examples directory. Aborting.
    exit 1
fi

EXAMPLE=simple
CHOICE=$1
if [ "$CHOICE" == "" ]; then
    read -e -p "Which example would you like to start? [$EXAMPLES] " CHOICE
fi

FOUND=0
for CHECK in $EXAMPLES; do
    if [ "$CHECK" == "$CHOICE" ]; then
        EXAMPLE=$CHECK
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo $CHOICE is not a valid example.
fi

echo Using example "$EXAMPLE".

if [ "$EXAMPLE" == "custom" ]; then
    # this doesn’t use plata’s contact model
    PLATAMODULES=${PLATAMODULES#"contact "}
fi

export DJANGO_SETTINGS_MODULE="$EXAMPLE.settings"

if [ ! -d "$EXAMPLE/migrations" ]; then
    echo This example is lacking migrations, i.e. it’s not initialized.
    if [ -d "../plata/shop/migrations" ]; then
        echo But plata contains migrations, probably from a different setup.
        read -e -p "May I delete them? [y/any] " CHOICE
            if [ "$CHOICE" == "y" ]; then
                        for PACK in $PLATAMODULES; do
                echo Deleting migrations from plata/$PACK
                rm -rf ../plata/$PACK/migrations
            done
        else
            echo "No harm done, but expect troubles."
        fi
    fi
    echo Making new migrations for example $EXAMPLE...
    python manage.py migrate
    python manage.py makemigrations $PLATAMODULES $EXAMPLE
    python manage.py migrate

    echo Last step: Create a new superuser. You can cancel this.
    python manage.py createsuperuser
else
    echo Existing migrations found. If there are problems, you might run reset-migrations.sh
fi

echo Starting website – please open localhost:9876 in your browser.
echo Please login at /admin and create some products first.

python manage.py runserver 9876
