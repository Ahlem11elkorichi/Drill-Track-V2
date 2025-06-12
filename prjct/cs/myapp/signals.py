from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import  Notification, Rapport, RapportImported, User, Forage, Phase, PhaseStandard
from django.utils import timezone
from django.db.models import Max
import pandas as pd
import re
from datetime import datetime, timedelta
import os

def normalize(s):
    """Helper function to normalize strings for comparison"""
    if s is None:
        return ""
    return re.sub(r"[\"'\s]", "", str(s)).lower()

@receiver(post_save, sender=RapportImported)
def process_imported_rapport(sender, instance, created, **kwargs):
    """
    Signal handler that automatically processes imported reports and creates notifications.
    This integrates the logic from import.py directly into the signal handler.
    """
    if created:
        try:
            # Process the Excel file and create Rapport, similar to your import.py
            file_path = instance.url.path
            df = pd.read_excel(file_path)
            
            # Extract data from Excel file
            def find_first_cell_with_date_prefix_or_fallback(df):
                pattern = r"^\s*date\s*:\s*.*"
                for i, row in df.iterrows():
                    for j, val in row.items():
                        if pd.isnull(val):
                            continue
                        if re.match(pattern, str(val), re.IGNORECASE):
                            match = re.search(r"\d{2}/\d{2}/\d{4}", str(val))
                            if match:
                                date_str = match.group()
                                try:
                                    return datetime.strptime(date_str, "%m/%d/%Y").date()
                                except ValueError:
                                    pass

                # Si aucune date n'est trouvée :
                try:
                    fallback_value = df.iat[58, 68]
                    return pd.to_datetime(fallback_value).date()
                except Exception:
                    return timezone.now().date()  # Default to today if all else fails
            
            # Extract all the required data from Excel
            date_rapport = find_first_cell_with_date_prefix_or_fallback(df)
            phase_actuelle = df.iat[8, 12]
            numrap = df.iat[2, 88]
            cout_actuel = df.iat[56, 87]
            coutCumul_actuel = df.iat[57, 87]
            depth = df.iat[4, 20]
            zone = df.iat[1, 34]
            current_operation = df.iat[43, 59]
            planned_operation = df.iat[56, 14]
            
            # Find or create Forage
            forage = Forage.objects.filter(zone=zone).order_by('date_debut').last()
            if forage is None:
                # Handle case when forage doesn't exist
                last_forage = Forage.objects.last()
                if last_forage:
                    last_forage.date_fin = date_rapport - timedelta(days=1)
                    last_forage.save()
                    
                
                forage = Forage.objects.create(
                    zone=zone,
                    description="description",
                    date_debut=date_rapport,
                    date_fin=date_rapport + timedelta(days=70),
                    cout_actuel=+cout_actuel,
                    duration_actuelle=+1,
                )
            
            # Create Rapport
            rapport = Rapport.objects.create(
                id_forage=forage,
                num_rapport=numrap,
                date_actuelle=date_rapport,
                nom_phase=phase_actuelle,
                id_rapport_imported=instance  # Link to the imported rapport
            )
            
            # Now handle Phase creation/update
            last_rapport = Rapport.objects.filter(id_forage=forage).order_by('date_actuelle').last()
            last_phase = Phase.objects.filter(id_forage=forage).order_by('id_phase').last()
            
            if last_rapport is not None and last_phase is not None:
                if normalize(last_rapport.nom_phase) in normalize(last_phase.id_phase_standard.nom_de_phase):
                    # Update existing phase
                    last_phase.delai_actuel = (rapport.date_actuelle - last_phase.date_debut).days
                    last_phase.cout_actuel = cout_actuel
                    last_phase.depth_actuel = depth
                    last_phase.cout_cumulatif_actuel = coutCumul_actuel
                    last_phase.current_operation = current_operation
                    last_phase.planned_operation = planned_operation
                    last_phase.etat="on progress"
                    last_phase.save()
                else:
                    # Create new phase for existing forage
                    try:
                         last_p = Phase.objects.filter(id_forage=forage).order_by('id_phase').last()
                         if last_p:
                             phase_standard = last_p.id_phase_standard
                             delai_previsionnel = phase_standard.delai_previstionel
                             delai_actuel = last_p.delai_actuel
                             if delai_previsionnel > 0:
                               pourcentage_depassement = ((delai_actuel - delai_previsionnel) / delai_previsionnel) * 100
                             else:
                               pourcentage_depassement = 0
              
                             if pourcentage_depassement <= 10:
                                last_p.etat="on time"
                             elif pourcentage_depassement <= 25:
                                last_p.etat = "slight delay"
                             else:
                                last_p.etat = "significant delay"
                             last_p.save()

                        
                         phase_std = PhaseStandard.objects.get(nom_de_phase__startswith=normalize(rapport.nom_phase[0:2]))
                         Phase.objects.create(
                            id_phase_standard=phase_std,
                            id_forage=forage,
                            delaiActuel=1,
                            depthActuel=depth,
                            date_debut=date_rapport,
                            cout_actuel=cout_actuel,
                            coutCumulatifActuel=coutCumul_actuel,
                            currentOperation=current_operation,
                            plannedOperation=planned_operation
                        )
                    except PhaseStandard.DoesNotExist:
                        print(f"PhaseStandard not found for {rapport.nom_phase[0:2]}")
            else:
                # Create new phase for new forage
                try:
                    phase_std = PhaseStandard.objects.get(nom_de_phase__startswith=phase_actuelle[0:2])
                    Phase.objects.create(
                        id_phase_standard=phase_std,
                        id_forage=forage,
                        delaiActuel=1,
                        cout_actuel=cout_actuel,
                        date_debut=date_rapport,
                        depthActuel=depth,
                        coutCumulatifActuel=coutCumul_actuel,
                        currentOperation=current_operation,
                        plannedOperation=planned_operation
                    )
                except PhaseStandard.DoesNotExist:
                    print(f"PhaseStandard not found for {phase_actuelle[0:2]}")
            
            # Create notifications for responsible users
            # Modified to match your Notification model structure without 'message' field
            responsables = User.objects.filter(role='responsable')
            for user in responsables:
                Notification.objects.create(
                    id_user=user,
                    id_rapport=rapport,
                    date_notif=timezone.now().date(),
                    analysed=False
                    # 'message' field removed as it's not in your model
                )
                
        except Exception as e:
            print(f"Error processing imported rapport: {str(e)}")
            import traceback
            traceback.print_exc()