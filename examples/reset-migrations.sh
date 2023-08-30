#!/bin/bash
EXAMPLES="custom oneprice simple staggered generic"
PLATAMODULES="contact discount shop"

if [ ! -d "staggered" ]; then
    echo It seems your current directory is not plata/examples. Aborting.
    exit 1
fi

read -e -p "Do you want to delete the migrations from all examples? [y/any] " CHOICE

if [ "$CHOICE" == "y" ]; then
    for EXPL in $EXAMPLES; do
        echo Deleting migrations from examples/$EXPL
        rm -rf $EXPL/migrations
    done
else
    echo "No harm done."
fi

if [ ! -d "../plata/shop/migrations" ]; then
    echo Plata migrations not found.
else
    read -e -p "Do you want to delete the migrations from plata? [y/any] " CHOICE

    if [ "$CHOICE" == "y" ]; then
        for PACK in $PLATAMODULES; do
            echo Deleting migrations from plata/$PACK
            rm -rf ../plata/$PACK/migrations
        done
    else
        echo "No harm done."
        exit 2
    fi
fi

read -e -p "Do you want to create new migrations? For which example? [$EXAMPLES] " CHOICE

if [ ! -d "$CHOICE" ]; then
    echo Example $CHOICE not found. Aborting.
    exit 4
fi

if [ "$CHOICE" == "custom" ]; then
    # this doesn’t use plata’s contact model
    PLATAMODULES=${PLATAMODULES#"contact "}
fi

export DJANGO_SETTINGS_MODULE="$CHOICE.settings"
echo "Please make sure that example/manage.py uses the right settings!"

echo Making new migrations for example $CHOICE...
python manage.py migrate
python manage.py makemigrations $PLATAMODULES $CHOICE
python manage.py migrate

echo Last step: Create a new superuser. You can cancel this.
python manage.py createsuperuser
