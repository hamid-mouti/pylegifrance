#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import os
import logging
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

import yaml

from importlib import resources

load_dotenv(override=True)

with resources.open_text('pylegifrance', 'config.yaml') as file:
    config = yaml.safe_load(file)

logging_level = config['logging']['level']
logging.basicConfig(level=logging_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging_level)


class LegiHandler:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # cls._instance = super(LegiHandler, cls).__new__(cls)
            cls._instance = super().__new__(cls)
            # Initialisation de l'instance unique
            cls._instance._initialize(*args, **kwargs)
        return cls._instance

    def _initialize(self):
        """
        Initialisation interne de l'instance unique.

        Returns
        -------
        LegiHandler.

        """
        self.client_id = os.getenv("CLIENT_ID")
        self.client_secret = os.getenv("CLIENT_SECRET")
        self.token = ''
        self.token_url = 'https://sandbox-oauth.piste.gouv.fr/api/oauth/token'
        self.api_url = 'https://sandbox-api.piste.gouv.fr/dila/legifrance/lf-engine-app'
        self.time_token = 0
        self.expires_in = 3600  # Valeur par défaut pour éviter une erreur

    def set_api_keys(self, legifrance_api_key=None, legifrance_api_secret=None):
       """
        Définit ou met à jour les clés API pour l'instance.

        Si les clés ne sont pas fournies, la méthode utilise les valeurs 
        actuelles, si elles existent.
        Si les valeurs actuelles n'existent pas, elle tente de les 
        récupérer à partir des variables d'environnement.

        Parameters
        ----------
        legifrance_api_key : str, optional
            Clé API Legifrance. Si None, conserve la valeur actuelle 
            ou tente de la récupérer depuis la variable d'environnement.
        legifrance_api_secret : str, optional
            Secret API Legifrance. Si None, conserve la valeur actuelle 
            ou tente de le récupérer depuis la variable d'environnement.
        """
 
      # Utiliser les clés existantes si de nouvelles clés ne sont pas fournies
       if legifrance_api_key is None:
            legifrance_api_key = self.client_id if self.client_id else os.getenv("LEGIFRANCE_CLIENT_ID")
       if legifrance_api_secret is None:
            legifrance_api_secret = self.client_secret if self.client_secret else os.getenv("LEGIFRANCE_CLIENT_SECRET")

       if not legifrance_api_key or not legifrance_api_secret:
           raise ValueError("Les clés de l'API Legifrance ne sont pas présentes")

       # Vérifie si les nouvelles clés sont différentes des clés existantes
       if (self.client_id != legifrance_api_key or
           self.client_secret != legifrance_api_secret):
           self.client_id = legifrance_api_key
           self.client_secret = legifrance_api_secret
           self._get_access()  # Renouveler le token uniquement si les clés ont changé

    def _get_access(self, attempts=3, delay=5):
        """
        Obtient un token d'accès pour l'API Legifrance.
        """
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'openid'
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        for i in range(attempts):
            response = requests.post(self.token_url, headers=headers, data=data)

            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get('access_token')
                self.time_token = time.time()
                self.expires_in = token_data.get('expires_in')

                logging.info(f"✅ Connexion réussie à l'API Legifrance! Token : {self.token}")
                return  # Succès, on sort de la fonction

            logging.error(f"❌ Tentative {i + 1} échouée: {response.status_code} - {response.text}")

            if i < attempts - 1:
                time.sleep(delay)  # On attend avant de réessayer

        raise Exception(f"❌ Échec de l'obtention du token après {attempts} tentatives.")

    def _update_client(self):
        """
        Fonction qui renouvelle le token 

        """

        elapsed_time = time.time() - self.time_token
        if elapsed_time >= self.expires_in:
            self.time_token = time.time()
            self._get_access()

    def call_api(self, route: str, data: str):

        self._update_client()
        headers = {
            'Authorization': f'Bearer {self.token}',
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        if data is not None:

            response = requests.post(f"{self.api_url}/{route}",headers=headers, json=data)

        if response.status_code >= 400 and response.status_code <= 500:
            raise Exception(f"Erreur client {response.status_code} - {response.text} lors de l'appel à l'API :"
                            f"\n Token: {self.token}, \nURL: {self.api_url}{route}")

        return response

    def ping(self, route: str = "list/ping"):
        # TODO: implémenter les pings selon documentation legifrance
        pass

    def get(self, route: str):
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        print(f"{self.api_url}{route}")
        response = requests.get(f"{self.api_url}{route}", headers=headers)
        response.raise_for_status()
        self.data = response.json()

        return response